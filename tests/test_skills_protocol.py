"""Protocol v2 skills ops and AgentResult.skills round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from vex_desktop.agent.errors import AgentError
from vex_desktop.agent.qt import AgentClient
from vex_desktop.agent.service import AgentService
from vex_desktop.agent.stub import StubBackend
from vex_desktop.protocol import (
    OPS,
    PROTOCOL_VERSION,
    AgentRequest,
    AgentResult,
    ProjectSnapshot,
)


def _service(tmp_path: Path, monkeypatch) -> AgentService:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from vex_desktop.platform_support import data_dir

    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    (root / "skills.json").write_text('{"enabled": [], "seeded": true}\n', encoding="utf-8")
    return AgentService(StubBackend())


def _write_md(path: Path, name: str, body: str, description: str = "") -> None:
    desc = f"description: {description}\n" if description else ""
    path.write_text(f"---\nname: {name}\n{desc}---\n{body}", encoding="utf-8")


def test_protocol_version_is_3():
    assert PROTOCOL_VERSION == 3
    for op in ("list_skills", "import_skill", "remove_skill", "set_skills"):
        assert op in OPS
    assert AgentRequest(op="list_skills").to_dict()["protocol"] == 3


def test_agent_result_skills_round_trip():
    skills = [
        {
            "id": "named",
            "name": "Named",
            "description": "A desc",
            "enabled": True,
            "chars": 5,
        }
    ]
    result = AgentResult(
        op="list_skills",
        success=True,
        message="1 skills active: named",
        snapshot=ProjectSnapshot(backend="stub"),
        skills=skills,
    )
    data = result.to_dict()
    assert data["skills"] == skills
    restored = AgentResult.from_dict(data)
    assert restored.skills == skills
    assert restored.op == "list_skills"
    assert restored.snapshot.backend == "stub"
    empty = AgentResult.from_dict(
        {"op": "snapshot", "success": True, "message": "", "snapshot": {}}
    )
    assert empty.skills == []


def test_list_skills_empty_catalog(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    result = service.handle("list_skills", {})
    assert result.success
    assert result.op == "list_skills"
    assert result.skills == []
    assert result.snapshot.backend == "stub"


def test_import_list_set_remove_skills(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    src = tmp_path / "named.md"
    _write_md(src, "Named", "Do X.\n", description="A desc")

    imported = service.handle("import_skill", {"path": str(src)})
    assert imported.success
    assert imported.op == "import_skill"
    assert imported.snapshot.backend == "stub"
    by_id = {row["id"]: row for row in imported.skills}
    assert "named" in by_id
    assert by_id["named"]["name"] == "Named"
    assert by_id["named"]["description"] == "A desc"
    assert by_id["named"]["enabled"] is False
    assert by_id["named"]["chars"] == len("Do X.\n")

    listed = service.handle("list_skills", {})
    assert [row["id"] for row in listed.skills] == ["named"]
    assert listed.skills[0]["enabled"] is False

    activated = service.handle("set_skills", {"ids": ["named"]})
    assert activated.success
    assert activated.op == "set_skills"
    assert "1 skills active: named" in activated.message
    assert any(row["id"] == "named" and row["enabled"] for row in activated.skills)

    persisted = AgentService(StubBackend()).handle("list_skills", {})
    assert any(row["id"] == "named" and row["enabled"] for row in persisted.skills)

    removed = service.handle("remove_skill", {"id": "named"})
    assert removed.success
    assert removed.skills == []
    leftover = service.handle("list_skills", {})
    assert leftover.skills == []
    assert not any(row["enabled"] for row in leftover.skills)


def test_set_skills_ignores_unknown_ids(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    src_a = tmp_path / "a.md"
    src_b = tmp_path / "b.md"
    _write_md(src_a, "Alpha", "A body\n")
    _write_md(src_b, "Beta", "B body\n")
    service.handle("import_skill", {"path": str(src_a)})
    service.handle("import_skill", {"path": str(src_b)})

    result = service.handle("set_skills", {"ids": ["a", "b", "nope"]})
    assert result.success
    assert "2 skills active: a, b" in result.message
    assert "nope" in result.message
    assert "unknown" in result.message.lower()
    enabled = [row["id"] for row in result.skills if row["enabled"]]
    assert enabled == ["a", "b"]
    assert "nope" not in enabled


def test_set_skills_message_notes_truncated_skill(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    src = tmp_path / "huge.md"
    _write_md(src, "Huge", "X" * 16001 + "\n")
    imported = service.handle("import_skill", {"path": str(src)})
    skill_id = imported.skills[0]["id"]
    result = service.handle("set_skills", {"ids": [skill_id]})
    assert result.success
    assert f"1 skills active: {skill_id}" in result.message
    assert f"{skill_id} truncated" in result.message


def test_import_skill_missing_path_raises(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    with pytest.raises(AgentError) as exc:
        service.handle("import_skill", {"path": str(tmp_path / "missing.md")})
    message = str(exc.value)
    assert message
    assert "not found" in message.lower()


@pytest.mark.parametrize("payload", [{}, {"path": ""}, {"path": None}])
def test_import_skill_blank_path_raises(tmp_path, monkeypatch, payload):
    service = _service(tmp_path, monkeypatch)
    with pytest.raises(AgentError) as exc:
        service.handle("import_skill", payload)
    message = str(exc.value)
    assert "not found" in message.lower()
    assert "skill.md" not in message.lower()
    from vex_desktop.platform_support import data_dir

    skills_dir = data_dir() / "skills"
    if skills_dir.is_dir():
        assert list(skills_dir.iterdir()) == []


def test_import_skill_unreadable_type_raises(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    bad = tmp_path / "notes.txt"
    bad.write_text("not a skill\n", encoding="utf-8")
    with pytest.raises(AgentError) as exc:
        service.handle("import_skill", {"path": str(bad)})
    message = str(exc.value).lower()
    assert message
    assert "unknown agent op" not in message


def test_remove_skill_missing_id_raises(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    with pytest.raises(AgentError) as exc:
        service.handle("remove_skill", {"id": "ghost"})
    assert "not found" in str(exc.value).lower()


def test_agent_client_skills_methods_exist():
    assert callable(AgentClient.list_skills)
    assert callable(AgentClient.import_skill)
    assert callable(AgentClient.remove_skill)
    assert callable(AgentClient.set_skills)


def test_agent_client_list_skills_roundtrip(qtbot, tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    client = AgentClient(service=service)
    seen: list[AgentResult] = []
    failed: list[str] = []
    client.result_ready.connect(seen.append)
    client.failed.connect(failed.append)
    try:
        client.list_skills()
        qtbot.waitUntil(lambda: bool(seen) or bool(failed), timeout=5000)
        assert failed == []
        assert seen[0].op == "list_skills"
        assert seen[0].success
        assert seen[0].skills == []
    finally:
        client.shutdown()
