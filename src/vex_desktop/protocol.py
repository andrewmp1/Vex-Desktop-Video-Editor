"""Frozen agent protocol.

JSON-serializable types shared by the PySide6 UI, the in-process service,
and a future stdio/subprocess host. No Qt and no vex_core imports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PROTOCOL_VERSION = 1

OPS = (
    "load_project",
    "process_command",
    "undo",
    "redo",
    "snapshot",
    "cancel",
    "set_config",
    "export",
)


@dataclass
class ProjectSnapshot:
    project_id: str | None = None
    project_name: str | None = None
    source_path: str | None = None
    working_file: str | None = None
    history: list[str] = field(default_factory=list)
    can_undo: bool = False
    can_redo: bool = False
    provider: str = "gemini"
    model: str = "gemini"
    backend: str = "stub"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectSnapshot:
        known = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        return cls(**known)


@dataclass
class ProgressEvent:
    op: str
    stage: str
    message: str
    tool: str | None = None
    fraction: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgressEvent:
        return cls(
            op=str(data.get("op") or ""),
            stage=str(data.get("stage") or ""),
            message=str(data.get("message") or ""),
            tool=data.get("tool"),
            fraction=data.get("fraction"),
        )


@dataclass
class AgentResult:
    op: str
    success: bool
    message: str
    snapshot: ProjectSnapshot
    tools_called: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    new_video: str | None = None
    exported_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["snapshot"] = self.snapshot.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentResult:
        snapshot_data = data.get("snapshot") or {}
        snapshot = (
            snapshot_data
            if isinstance(snapshot_data, ProjectSnapshot)
            else ProjectSnapshot.from_dict(snapshot_data)
        )
        return cls(
            op=str(data.get("op") or ""),
            success=bool(data.get("success")),
            message=str(data.get("message") or ""),
            snapshot=snapshot,
            tools_called=list(data.get("tools_called") or []),
            suggestions=list(data.get("suggestions") or []),
            new_video=data.get("new_video"),
            exported_path=data.get("exported_path"),
        )


@dataclass
class AgentRequest:
    op: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": PROTOCOL_VERSION,
            "type": "request",
            "id": self.id,
            "op": self.op,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentRequest:
        return cls(
            op=str(data.get("op") or ""),
            payload=dict(data.get("payload") or {}),
            id=str(data.get("id") or ""),
        )
