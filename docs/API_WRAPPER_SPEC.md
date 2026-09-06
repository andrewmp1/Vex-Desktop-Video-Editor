# Agent protocol

The GUI talks only to `AgentClient`. It never constructs a Vex class and never imports `vex_core`.

`PROTOCOL_VERSION = 3` (additive: skills ops, `pack_project` / `unpack_project`).

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
client.list_skills()
client.import_skill("/path/to/SKILL.md")
client.set_skills(["youtube-metadata"])
client.remove_skill("youtube-metadata")
client.pack_project("/tmp/edit.vex")
client.unpack_project("/tmp/edit.vex")
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

### Skills ops

Handled by `AgentService` (local disk only; no backend LLM call). Catalog rows are returned on `AgentResult.skills`.

| Op | Payload | Behavior |
|----|---------|----------|
| `list_skills` | `{}` | Scan `data_dir()/skills`, return catalog |
| `import_skill` | `{"path": "..."}` | Copy a local `.md` or skill folder into the store |
| `remove_skill` | `{"id": "..."}` | Delete from disk and the enabled set |
| `set_skills` | `{"ids": ["a", "b"]}` | Persist enabled ids to `data_dir()/skills.json` |

Each catalog entry: `id`, `name`, `description`, `enabled`, `chars`, plus additive `body` (markdown after frontmatter, for UI preview).

Skills inject only on `process_command` (composed preamble + user command). `export`, `undo`, `redo`, and `load_project` are unchanged. Local files only — no marketplace or URL fetch.

On Linux, skills live under `$XDG_DATA_HOME/Vex/skills` (typically `~/.local/share/Vex/skills`).

### Project bundle ops

| Op | Payload | Behavior |
|----|---------|----------|
| `pack_project` | `{"output_path": "..."}` | Zip the current Vex project folder (or stub working file) to a `.vex` file. Result `exported_path` is the zip. |
| `unpack_project` | `{"path": "..."}` | Extract into `AGENT_PROJECTS_DIR` / `~/.video-agent/projects`, then load the project. |

A `.vex` file is a zip with `vex-bundle.json` (`format: 1`, `project_id`, `kind`).

## Backends

`create_backend()` reads `VEX_AGENT_BACKEND` (`auto` | `stub` | `core`, default `auto`). Auto uses the local Vex tree when `agent.py` is present, otherwise stub (see Architecture).

## Errors

`AgentError`, `ProjectError`, `FFmpegError`, `CoreUnavailable` — messages are safe to show in the chat pane.
