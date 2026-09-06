"""Pack and unpack .vex project zips. Qt-free."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from vex_desktop.agent.errors import AgentError

MANIFEST_NAME = "vex-bundle.json"
BUNDLE_FORMAT = 1


def pack_working_file(working_file: Path | str, output_path: Path | str, project_id: str) -> Path:
    source = Path(working_file)
    if not source.is_file():
        raise AgentError(f"Working file not found: {source}")
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": BUNDLE_FORMAT,
        "project_id": project_id,
        "kind": "working_file",
        "working_name": source.name,
    }
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2) + "\n")
        zf.write(source, f"{project_id}/working/{source.name}")
    return dest


def pack_project_dir(project_dir: Path | str, output_path: Path | str, project_id: str) -> Path:
    root = Path(project_dir)
    if not root.is_dir():
        raise AgentError(f"Project folder not found: {root}")
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": BUNDLE_FORMAT,
        "project_id": project_id,
        "kind": "project",
    }
    prefix = f"{project_id}/"
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2) + "\n")
        for path in root.rglob("*"):
            if path.is_file():
                zf.write(path, prefix + str(path.relative_to(root)))
    return dest


def unpack_bundle(bundle_path: Path | str, dest_root: Path | str) -> dict[str, Any]:
    archive = Path(bundle_path)
    if not archive.is_file():
        raise AgentError("Project file not found.")
    dest = Path(dest_root)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            if MANIFEST_NAME not in names:
                raise AgentError("Not a Vex project file.")
            manifest = json.loads(zf.read(MANIFEST_NAME))
            if not isinstance(manifest, dict) or int(manifest.get("format") or 0) != BUNDLE_FORMAT:
                raise AgentError("Unsupported .vex format.")
            project_id = str(manifest.get("project_id") or "").strip()
            kind = str(manifest.get("kind") or "")
            if not project_id or kind not in {"project", "working_file"}:
                raise AgentError("Invalid .vex manifest.")
            target = dest / project_id
            if target.exists():
                raise AgentError(f"Project already exists: {project_id}")
            for name in names:
                if name == MANIFEST_NAME or name.endswith("/"):
                    continue
                parts = Path(name).parts
                if not parts or Path(name).is_absolute() or ".." in parts:
                    raise AgentError("Invalid .vex archive.")
                zf.extract(name, dest)
    except zipfile.BadZipFile as exc:
        raise AgentError("Not a Vex project file.") from exc
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AgentError("Invalid .vex manifest.") from exc

    if kind == "project":
        folder = dest / project_id
        if not folder.is_dir():
            raise AgentError("Bundle has no project folder.")
        return {"project_id": project_id, "kind": kind, "load_path": project_id}
    working_name = str(manifest.get("working_name") or "")
    loaded = dest / project_id / "working" / working_name
    if not working_name or not loaded.is_file():
        raise AgentError("Bundle has no working file.")
    return {"project_id": project_id, "kind": kind, "load_path": str(loaded)}
