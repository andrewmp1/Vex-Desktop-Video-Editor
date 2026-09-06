class AgentError(Exception):
    """User-facing agent failure. Safe to show in the chat pane."""


class FFmpegError(AgentError):
    pass


class ProjectError(AgentError):
    pass


class CoreUnavailable(AgentError):
    """vex_core is not on disk or failed to import."""
