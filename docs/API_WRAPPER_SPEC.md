# Agent protocol

The GUI talks only to `AgentClient`. It never constructs a Vex class and never imports `vex_core`.

## Client (Qt)

```python
from vex_desktop.agent.qt import AgentClient

client = AgentClient()
client.progress.connect(on_progress)       # ProgressEvent
client.result_ready.connect(on_result)     # AgentResult
client.failed.connect(on_failed)           # str
client.busy_changed.connect(on_busy)       # bool

client.load_project(path)
client.process_command("Trim the first 10 seconds")
client.process_command("export for youtube")
client.export("youtube_1080p")
client.undo()
client.redo()
client.set_config("gemini", "gemma-4-31b-it")
client.cancel()
client.shutdown()
```

Every method returns immediately. Work runs on a `QThread` inside `AgentService`.

## Service (no Qt)

`AgentService.handle(op, payload, progress) -> AgentResult`

Ops are listed in `vex_desktop.protocol.OPS`. Types are JSON-serializable so the same service can run over stdio:

```bash
python -m vex_desktop.agent
```

Each stdin line is `{"op": "process_command", "payload": {"command": "..."}}`.
Stdout lines are `{"type": "progress"|"result"|"error", ...}`.

## Backends

`create_backend()` reads `VEX_AGENT_BACKEND` (`auto` | `stub` | `core`, default `auto`). Auto uses the local Vex tree when `agent.py` is present, otherwise stub (see Architecture).

## Errors

`AgentError`, `ProjectError`, `FFmpegError`, `CoreUnavailable` — messages are safe to show in the chat pane.
