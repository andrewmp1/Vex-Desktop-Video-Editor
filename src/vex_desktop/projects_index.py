"""Read Vex CLI projects from disk. Does not import vex_core or start jobs."""

from __future__ import annotations

import json
from pathlib import Path

from vex_desktop.platform_support import vex_projects_dir


def list_projects(limit: int = 40) -> list[dict]:
    root = vex_projects_dir()
    if not root.is_dir():
        return []
    items: list[dict] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        payload_path = child / f"{child.name}.json"
        if not payload_path.is_file():
            continue
        try:
            data = json.loads(payload_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        artifacts = data.get("artifacts") if isinstance(data.get("artifacts"), dict) else {}
        working = str(data.get("working_file") or "")
        items.append(
            {
                "project_id": str(data.get("project_id") or child.name),
                "project_name": str(data.get("project_name") or child.name),
                "updated_at": str(data.get("updated_at") or ""),
                "working_file": working,
                "working_exists": Path(working).is_file() if working else False,
                "source_url": str(artifacts.get("source_url") or ""),
                "timeline_ops": len(data.get("timeline") or []),
            }
        )
    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return items[:limit]
