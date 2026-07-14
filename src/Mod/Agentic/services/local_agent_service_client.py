"""Thin client/process manager for the local Agentic service."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


@dataclass
class LocalAgentServiceClient:
    base_url: str
    token: str
    process: subprocess.Popen | None = None

    def health(self) -> dict[str, Any]:
        return self._json_request("GET", "/health")

    def plan_freecad_agent_episode(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request("POST", "/v1/freecad/plan", payload)

    def close(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

    def _json_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"X-Agentic-IPC-Token": self.token}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"local agent IPC HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"local agent IPC connection failed: {exc.reason}") from exc


class LocalAgentServiceSession:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.client: LocalAgentServiceClient | None = None

    def __enter__(self) -> LocalAgentServiceClient:
        self.client = start_local_agent_service(self.repo_root)
        return self.client

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.client is not None:
            self.client.close()


def start_local_agent_service(repo_root: Path) -> LocalAgentServiceClient:
    existing_url = os.environ.get("AGENTIC_CAD_SERVICE_URL", "").rstrip("/")
    existing_token = os.environ.get("AGENTIC_CAD_SERVICE_TOKEN", "")
    if existing_url and existing_token:
        client = LocalAgentServiceClient(existing_url, existing_token)
        client.health()
        return client

    python_executable = os.environ.get("AGENTIC_CAD_SERVICE_PYTHON") or _default_python()
    token = secrets.token_urlsafe(32)
    ready_dir = Path(tempfile.mkdtemp(prefix="agentic-cad-service-"))
    ready_file = ready_dir / "ready.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = _prepend_pythonpath(str(repo_root), env.get("PYTHONPATH", ""))
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    process = subprocess.Popen(
        [
            python_executable,
            "-m",
            "backend.freecad_bridge.local_agent_ipc_service",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--token",
            token,
            "--ready-file",
            str(ready_file),
        ],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ready = _wait_for_ready_file(ready_file, process)
        client = LocalAgentServiceClient(str(ready["base_url"]).rstrip("/"), token, process=process)
        client.health()
        return client
    except Exception:
        if process.poll() is None:
            process.terminate()
        raise


def _wait_for_ready_file(ready_file: Path, process: subprocess.Popen) -> dict[str, Any]:
    deadline = time.monotonic() + float(os.environ.get("AGENTIC_CAD_SERVICE_STARTUP_TIMEOUT_S", "60"))
    while time.monotonic() < deadline:
        if ready_file.is_file():
            return json.loads(ready_file.read_text(encoding="utf-8"))
        if process.poll() is not None:
            raise RuntimeError(f"local agent service exited early: {process.returncode}")
        time.sleep(0.05)
    raise TimeoutError("local agent service did not become ready")


def _prepend_pythonpath(path: str, existing: str) -> str:
    if not existing:
        return path
    return path + os.pathsep + existing


def _default_python() -> str:
    if sys.executable and Path(sys.executable).name not in {"FreeCAD", "FreeCADCmd"}:
        return sys.executable
    return "python3"
