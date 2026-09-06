"""Blocking agent service. No Qt.

The GUI talks to this through AgentClient (QThread) or JSONL stdio.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from vex_desktop.agent.backend import AgentBackend
from vex_desktop.agent.core import VexCoreBackend, is_core_available
from vex_desktop.agent.errors import AgentError, CoreUnavailable
from vex_desktop.agent.stub import StubBackend
from vex_desktop.exporting import looks_like_export
from vex_desktop.platform_support import data_dir
from vex_desktop.protocol import OPS, AgentResult, ProgressEvent
from vex_desktop.skills import SkillState, SkillStore, compose_preamble, maybe_seed_bundled_skills


ProgressFn = Callable[[ProgressEvent], None]


def create_backend(mode: str | None = None) -> AgentBackend:
    selected = (mode or os.environ.get("VEX_AGENT_BACKEND") or "auto").strip().lower()
    if selected == "stub":
        return StubBackend()
    if selected == "core":
        return VexCoreBackend()
    if selected == "auto":
        if is_core_available():
            try:
                return VexCoreBackend()
            except CoreUnavailable:
                return StubBackend()
        return StubBackend()
    raise AgentError(f"Unknown agent backend: {selected}")


class AgentService:
    def __init__(self, backend: AgentBackend | None = None):
        self._backend = backend or create_backend()
        root = data_dir()
        self._store = SkillStore(root / "skills")
        self._state = SkillState(root)
        maybe_seed_bundled_skills(self._store, self._state)

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def cancel(self) -> None:
        self._backend.cancel()

    def handle(self, op: str, payload: dict, progress: ProgressFn | None = None) -> AgentResult:
        if op not in OPS:
            raise AgentError(f"Unknown agent op: {op}")
        emit = progress or (lambda _event: None)
        if op == "cancel":
            self.cancel()
            return AgentResult(
                op="cancel",
                success=True,
                message="Cancel requested.",
                snapshot=self._backend.snapshot(),
            )
        if op == "snapshot":
            snapshot = self._backend.snapshot()
            return AgentResult(
                op="snapshot",
                success=True,
                message="",
                snapshot=snapshot,
                new_video=snapshot.working_file,
            )
        if op == "load_project":
            return self._backend.load_project(str(payload.get("video_path") or ""), emit)
        if op == "process_command":
            return self._process_command(str(payload.get("command") or ""), emit)
        if op == "undo":
            return self._backend.undo(emit)
        if op == "redo":
            return self._backend.redo(emit)
        if op == "set_config":
            return self._backend.set_config(
                str(payload.get("provider") or ""),
                str(payload.get("model") or ""),
            )
        if op == "export":
            preset = str(payload.get("preset") or payload.get("preset_name") or "youtube_1080p")
            output_path = payload.get("output_path")
            return self._backend.export(
                preset,
                str(output_path) if output_path else None,
                emit,
            )
        if op == "list_skills":
            return self._list_skills()
        if op == "import_skill":
            return self._import_skill(str(payload.get("path") or ""))
        if op == "remove_skill":
            return self._remove_skill(str(payload.get("id") or ""))
        if op == "set_skills":
            return self._set_skills(payload.get("ids"))
        raise AgentError(f"Unhandled op: {op}")

    def _catalog(self) -> list[dict]:
        enabled = set(self._state.enabled)
        rows: list[dict] = []
        for info in self._store.scan():
            try:
                body = self._store.body(info)
            except OSError:
                body = ""
            rows.append(
                {
                    "id": info.id,
                    "name": info.name,
                    "description": info.description,
                    "enabled": info.id in enabled,
                    "chars": info.chars,
                    "body": body,
                }
            )
        return rows

    def _skills_result(self, op: str, message: str) -> AgentResult:
        return AgentResult(
            op=op,
            success=True,
            message=message,
            snapshot=self._backend.snapshot(),
            skills=self._catalog(),
        )

    def _missing_enabled(self) -> list[str]:
        known = {info.id for info in self._store.scan()}
        return [skill_id for skill_id in self._state.enabled if skill_id not in known]

    def _enabled_pairs(self) -> list[tuple[str, str]]:
        by_id = {info.id: info for info in self._store.scan()}
        pairs: list[tuple[str, str]] = []
        for skill_id in self._state.enabled:
            info = by_id.get(skill_id)
            if info is None:
                continue
            pairs.append((info.name, self._store.body(info)))
        return pairs

    def _process_command(self, command: str, emit: ProgressFn) -> AgentResult:
        if looks_like_export(command):
            return self._backend.process_command(command, emit)
        composed, _warnings = compose_preamble(self._enabled_pairs(), command)
        return self._backend.process_command(composed, emit)

    def _list_skills(self) -> AgentResult:
        missing = self._missing_enabled()
        message = f"Missing skills skipped: {', '.join(missing)}" if missing else ""
        return self._skills_result("list_skills", message)

    def _import_skill(self, path: str) -> AgentResult:
        if not path.strip():
            raise AgentError("Skill file not found.")
        try:
            info = self._store.import_path(path)
        except FileNotFoundError:
            raise AgentError("Skill file not found.") from None
        except ValueError as exc:
            raise AgentError(str(exc)) from None
        except OSError:
            raise AgentError("Could not import skill.") from None
        return self._skills_result("import_skill", f"Imported {info.name}.")

    def _remove_skill(self, skill_id: str) -> AgentResult:
        try:
            self._store.remove(skill_id)
        except FileNotFoundError:
            raise AgentError("Skill not found.") from None
        except OSError:
            raise AgentError("Could not remove skill.") from None
        if skill_id in self._state.enabled:
            self._state.enabled = [item for item in self._state.enabled if item != skill_id]
            self._state.save()
        return self._skills_result("remove_skill", f"Removed {skill_id}.")

    def _set_skills(self, raw_ids: object) -> AgentResult:
        if raw_ids is None:
            raw_ids = []
        if not isinstance(raw_ids, list):
            raise AgentError("ids must be a list of skill ids.")
        requested = [str(item) for item in raw_ids]
        known = {info.id: info for info in self._store.scan()}
        active: list[str] = []
        unknown: list[str] = []
        seen: set[str] = set()
        for skill_id in requested:
            if skill_id in seen:
                continue
            seen.add(skill_id)
            if skill_id in known:
                active.append(skill_id)
            else:
                unknown.append(skill_id)
        self._state.enabled = active
        self._state.save()

        pairs = [(known[skill_id].name, self._store.body(known[skill_id])) for skill_id in active]
        _text, warnings = compose_preamble(pairs, "")
        truncated = [
            skill_id
            for skill_id in active
            if any("truncated" in warning.lower() and known[skill_id].name in warning for warning in warnings)
        ]
        if active:
            message = f"{len(active)} skills active: {', '.join(active)}"
        else:
            message = "0 skills active"
        if truncated:
            message += f" ({', '.join(truncated)} truncated)"
        if unknown:
            message += f". Unknown skill ids ignored: {', '.join(unknown)}"
        return self._skills_result("set_skills", message)
