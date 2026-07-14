"""Minimal backend client for the FreeCAD plugin Phase 0 path."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import error, parse, request


@dataclass
class AgenticApiConfig:
    """Runtime config for talking to the local agentic-cad backend."""

    base_url: str = "http://127.0.0.1:8000"
    api_key: str = ""

    @classmethod
    def from_environment(cls) -> "AgenticApiConfig":
        return cls(
            base_url=os.environ.get("AGENTIC_CAD_API_URL", cls.base_url).rstrip("/"),
            api_key=os.environ.get("AGENTIC_CAD_API_KEY", ""),
        )


class AgenticApiClient:
    """Thin synchronous client for the local agentic-cad backend."""

    def __init__(self, config: AgenticApiConfig | None = None):
        self.config = config or AgenticApiConfig.from_environment()

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}{path}"

    def _json_request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        req = request.Request(
            self._url(path),
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Backend connection failed: {exc.reason}") from exc

    def _get_json(self, path: str) -> dict[str, Any]:
        headers = {"X-API-Key": self.config.api_key} if self.config.api_key else {}
        req = request.Request(self._url(path), headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Backend connection failed: {exc.reason}") from exc

    def health(self) -> dict[str, Any]:
        return self._get_json("/api/health")

    def create_project(self, name: str = "FreeCAD Plugin Session") -> str:
        data = self._json_request("/api/projects", {"name": name})
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "Project creation failed"))
        return str(data["project"]["id"])

    def stream_chat(self, message: str, project_id: str) -> list[dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        req = request.Request(
            self._url("/api/chat"),
            data=json.dumps({"message": message, "project_id": project_id}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        events: list[dict[str, Any]] = []
        try:
            with request.urlopen(req, timeout=1800) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Backend connection failed: {exc.reason}") from exc
        return events

    def get_project(self, project_id: str) -> dict[str, Any]:
        data = self._get_json(f"/api/projects/{parse.quote(project_id)}")
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "Project fetch failed"))
        return data["project"]

    def plan_freecad(
        self,
        prompt: str,
        document_context: dict[str, Any],
        capabilities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = self._json_request(
            "/api/freecad/plan",
            {
                "prompt": prompt,
                "document_context": document_context,
                "capabilities": capabilities,
            },
        )
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "FreeCAD planning failed"))
        return data["plan"]

    def run_freecad_agent_episode(
        self,
        prompt: str,
        document_context: dict[str, Any],
        capabilities: list[dict[str, Any]],
        *,
        approved: bool = False,
        simulate_execution: bool = True,
        task_id: str = "freecad-plugin-agent-episode",
    ) -> dict[str, Any]:
        data = self._json_request(
            "/api/freecad/agent/episode",
            {
                "task_id": task_id,
                "prompt": prompt,
                "document_context": document_context,
                "capabilities": capabilities,
                "approved": approved,
                "simulate_execution": simulate_execution,
            },
        )
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "FreeCAD agent episode failed"))
        return data["episode"]

    def apply_freecad_human_review(self, context: dict[str, Any]) -> dict[str, Any]:
        data = self._json_request(
            "/api/freecad/human-review/apply",
            {
                "candidate_report_path": str(context["candidate_report_path"]),
                "decisions_path": str(context["decisions_path"]),
                "layout_ir_path": str(context["layout_ir_path"]),
                "constraint_ir_path": str(context["constraint_ir_path"]),
                "part_ir_path": str(context["part_ir_path"]),
                "part_model_path": str(context["part_model_path"]),
                "part_manifest_path": str(context["part_manifest_path"]),
                "hardware_model_path": str(context["hardware_model_path"]),
                "hardware_manifest_path": str(context["hardware_manifest_path"]),
                "workspace_dir": str(context["workspace_dir"]),
            },
        )
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "FreeCAD human-review apply failed"))
        return data["report"]

    def generate(self, prompt: str) -> dict[str, Any]:
        project_id = self.create_project()
        events = self.stream_chat(prompt, project_id)
        project = self.get_project(project_id)
        latest_model = project.get("latest_model") or {}
        return {
            "project_id": project_id,
            "events": events,
            "project": project,
            "latest_model": latest_model,
            "exports": latest_model.get("exports") or {},
        }
