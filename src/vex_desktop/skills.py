"""Local Agent Skills: scan, import, state, and preamble composition."""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SkillInfo:
    id: str
    name: str
    description: str
    path: Path
    chars: int


_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z",
    re.DOTALL,
)
_NAME_RE = re.compile(r"^name:\s*(.*)$", re.MULTILINE)
_DESC_RE = re.compile(r"^description:\s*(.*)$", re.MULTILINE)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_frontmatter(text: str, fallback_name: str) -> tuple[str, str, str]:
    """Return (name, description, body). Missing/malformed → stem name, empty desc."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return fallback_name, "", text
    meta, body = match.group(1), match.group(2)
    name_m = _NAME_RE.search(meta)
    desc_m = _DESC_RE.search(meta)
    name = _strip_quotes(name_m.group(1)) if name_m else fallback_name
    description = _strip_quotes(desc_m.group(1)) if desc_m else ""
    if not name:
        name = fallback_name
    return name, description, body


def _skill_md_path(skill_path: Path) -> Path:
    if skill_path.is_dir():
        return skill_path / "SKILL.md"
    return skill_path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flatten_references(skill_dir: Path) -> str:
    refs = skill_dir / "references"
    if not refs.is_dir():
        return ""
    parts: list[str] = []
    for child in sorted(refs.iterdir(), key=lambda p: p.name.lower()):
        if child.is_file():
            parts.append(_read_text(child))
    if not parts:
        return ""
    return "\n".join(parts)


def _unique_id(skills_dir: Path, base: str) -> str:
    candidate = base
    n = 2
    while (skills_dir / candidate).exists() or (skills_dir / f"{candidate}.md").exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


class SkillStore:
    def __init__(self, skills_dir: Path | str) -> None:
        self.skills_dir = Path(skills_dir)

    def scan(self) -> list[SkillInfo]:
        if not self.skills_dir.is_dir():
            return []
        infos: list[SkillInfo] = []
        for child in self.skills_dir.iterdir():
            info = self._info_for_entry(child)
            if info is not None:
                infos.append(info)
        infos.sort(key=lambda s: s.name.lower())
        return infos

    def _info_for_entry(self, path: Path) -> SkillInfo | None:
        if path.is_file() and path.suffix.lower() == ".md":
            skill_id = path.stem
            md_path = path
        elif path.is_dir() and (path / "SKILL.md").is_file():
            skill_id = path.name
            md_path = path / "SKILL.md"
        else:
            return None
        try:
            text = _read_text(md_path)
        except OSError:
            return None
        name, description, body = _parse_frontmatter(text, skill_id)
        full_body = body
        if path.is_dir():
            refs = _flatten_references(path)
            if refs:
                full_body = body + ("\n" if body and not body.endswith("\n") else "") + refs
        return SkillInfo(
            id=skill_id,
            name=name,
            description=description,
            path=path,
            chars=len(full_body),
        )

    def body(self, skill: SkillInfo) -> str:
        md_path = _skill_md_path(skill.path)
        text = _read_text(md_path)
        _, _, body = _parse_frontmatter(text, skill.id)
        if skill.path.is_dir():
            refs = _flatten_references(skill.path)
            if refs:
                if body and not body.endswith("\n"):
                    body += "\n"
                body += refs
        return body

    def import_path(self, src: str | Path) -> SkillInfo:
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        source = Path(src)
        if not source.exists():
            raise FileNotFoundError(f"Skill path not found: {source}")

        if source.is_file():
            if source.suffix.lower() != ".md":
                raise ValueError(f"Expected a .md file or skill folder: {source}")
            base_id = source.stem
            skill_id = _unique_id(self.skills_dir, base_id)
            dest_dir = self.skills_dir / skill_id
            dest_dir.mkdir(parents=True, exist_ok=False)
            shutil.copy2(source, dest_dir / "SKILL.md")
            info = self._info_for_entry(dest_dir)
            assert info is not None
            return info

        if source.is_dir():
            base_id = source.name
            skill_id = _unique_id(self.skills_dir, base_id)
            dest_dir = self.skills_dir / skill_id
            shutil.copytree(source, dest_dir)
            info = self._info_for_entry(dest_dir)
            if info is None:
                shutil.rmtree(dest_dir, ignore_errors=True)
                raise ValueError(f"Folder has no SKILL.md: {source}")
            return info

        raise ValueError(f"Unsupported skill path: {source}")

    def remove(self, skill_id: str) -> None:
        folder = self.skills_dir / skill_id
        bare = self.skills_dir / f"{skill_id}.md"
        if folder.is_dir():
            shutil.rmtree(folder)
        elif bare.is_file():
            bare.unlink()
        else:
            raise FileNotFoundError(f"Skill not found: {skill_id}")


class SkillState:
    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "skills.json"
        self.enabled: list[str] = []
        self.seeded: bool = False
        self.load()

    def load(self) -> None:
        if not self.path.is_file():
            self.enabled = []
            self.seeded = False
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            self.enabled = []
            self.seeded = False
            return
        if not isinstance(data, dict):
            self.enabled = []
            self.seeded = False
            return
        enabled = data.get("enabled", [])
        if isinstance(enabled, list):
            self.enabled = [str(x) for x in enabled]
        else:
            self.enabled = []
        self.seeded = bool(data.get("seeded", False))

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {"enabled": list(self.enabled), "seeded": bool(self.seeded)}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def bundled_skills_dir() -> Path:
    from vex_desktop.platform_support import repo_root

    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "assets" / "skills")
    root = repo_root()
    candidates.append(root / "assets" / "skills")
    candidates.append(root / "_internal" / "assets" / "skills")
    for path in candidates:
        if path.is_dir():
            return path
    return root / "assets" / "skills"


def maybe_seed_bundled_skills(
    store: SkillStore,
    state: SkillState,
    bundled: Path | str | None = None,
) -> None:
    """Copy packaged examples into the store once. Never reseed after deletion."""
    if state.seeded:
        return
    src_root = Path(bundled) if bundled is not None else bundled_skills_dir()
    store.skills_dir.mkdir(parents=True, exist_ok=True)
    if src_root.is_dir():
        existing = {child.name for child in store.skills_dir.iterdir()}
        for child in sorted(src_root.iterdir(), key=lambda path: path.name.lower()):
            if child.is_dir():
                key = child.name
            elif child.is_file() and child.suffix.lower() == ".md":
                key = child.stem
            else:
                continue
            if key in existing or f"{key}.md" in existing:
                continue
            try:
                store.import_path(child)
            except (FileNotFoundError, ValueError, OSError):
                continue
    state.seeded = True
    state.save()


def compose_preamble(
    skills: Sequence[tuple[str, str]] | Iterable[tuple[str, str]],
    command: str,
    per_cap: int = 16000,
    total_cap: int = 16000,
) -> tuple[str, list[str]]:
    skill_list = list(skills)
    if not skill_list:
        return command, []

    warnings: list[str] = []
    blocks: list[str] = []
    running = 0

    for name, body in skill_list:
        if running >= total_cap:
            warnings.append(
                f"Total skill budget ({total_cap} chars) reached; skipped remaining skills"
            )
            break

        content = body
        if len(content) > per_cap:
            marker = f"[skill {name} truncated]"
            # Keep marker inside per_cap so truncated skills still fit when
            # per_cap <= total_cap (defaults are equal).
            body_limit = max(0, per_cap - len(marker))
            content = content[:body_limit] + marker
            warnings.append(
                f"Skill '{name}' truncated to {per_cap} characters (per-skill cap)"
            )

        if running + len(content) > total_cap:
            warnings.append(
                f"Total skill budget ({total_cap} chars) reached; skipped remaining skills"
            )
            break

        running += len(content)
        blocks.append(f"=== Skill: {name} ===\n{content}\n=== End skill: {name} ===")

    header = (
        "Active skills for this session follow. Follow them when relevant to\n"
        "the user's request; otherwise ignore them.\n"
    )
    preamble = header + "\n" + "\n\n".join(blocks) + "\n\n" + f"User command: {command}"
    return preamble, warnings
