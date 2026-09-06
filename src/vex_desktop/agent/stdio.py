"""JSONL stdio host for the agent service.

Each stdin line is an AgentRequest. Progress, result, and error envelopes
are written to stdout. This is the subprocess-shaped API; the desktop UI
uses the same AgentService in-process via AgentClient.
"""

from __future__ import annotations

import json
import sys

from vex_desktop.agent.errors import AgentError
from vex_desktop.agent.service import AgentService
from vex_desktop.protocol import PROTOCOL_VERSION, AgentRequest, ProgressEvent


def serve_stdio(service: AgentService | None = None) -> int:
    agent = service or AgentService()
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            request = AgentRequest.from_dict(json.loads(line))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            _emit({"type": "error", "message": f"Invalid request: {exc}"})
            continue

        def progress(event: ProgressEvent) -> None:
            _emit({"type": "progress", "id": request.id, **event.to_dict()})

        try:
            result = agent.handle(request.op, request.payload, progress)
        except AgentError as exc:
            _emit({"type": "error", "id": request.id, "message": str(exc)})
            continue
        _emit({"type": "result", "id": request.id, **result.to_dict()})
    return 0


def _emit(payload: dict) -> None:
    payload.setdefault("protocol", PROTOCOL_VERSION)
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
