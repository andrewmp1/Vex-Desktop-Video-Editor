"""Agent package. UI code imports AgentClient from vex_desktop.agent.qt."""

from vex_desktop.agent.errors import AgentError, CoreUnavailable, FFmpegError, ProjectError
from vex_desktop.agent.service import AgentService, create_backend
from vex_desktop.protocol import AgentResult, ProgressEvent, ProjectSnapshot

__all__ = [
    "AgentError",
    "AgentResult",
    "AgentService",
    "CoreUnavailable",
    "FFmpegError",
    "ProgressEvent",
    "ProjectError",
    "ProjectSnapshot",
    "create_backend",
]
