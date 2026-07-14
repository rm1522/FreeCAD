"""FreeCAD document bridge helpers for importing generated files."""

from __future__ import annotations

import os
import tempfile
from urllib import request


def import_step_from_url(step_url: str, base_url: str) -> str:
    """Download a STEP file from the backend and insert it into the active document."""

    import FreeCAD  # type: ignore
    import ImportGui  # type: ignore

    absolute_url = f"{base_url}{step_url}" if step_url.startswith("/") else step_url
    with request.urlopen(absolute_url, timeout=300) as resp:
        data = resp.read()

    fd, temp_path = tempfile.mkstemp(suffix=".step", prefix="agentic_cad_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)

        doc = FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument("AgenticCAD")

        ImportGui.insert(temp_path, doc.Name)
        doc.recompute()
        return temp_path
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
