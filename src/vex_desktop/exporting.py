"""Export preset names shared with Vex's intent compiler."""

from __future__ import annotations

import re

PRESETS = (
    "youtube_1080p",
    "youtube_4k",
    "instagram_reels",
    "instagram_square",
    "tiktok",
    "twitter_x",
    "podcast_audio",
)

PRESET_LABELS = {
    "youtube_1080p": "YouTube 1080p",
    "youtube_4k": "YouTube 4K",
    "instagram_reels": "Instagram Reels",
    "instagram_square": "Instagram Square",
    "tiktok": "TikTok",
    "twitter_x": "X",
    "podcast_audio": "Podcast audio",
}

PRESET_SUFFIXES = {
    "podcast_audio": ".mp3",
}

DEFAULT_PRESET = "youtube_1080p"
DEFAULT_SUFFIX = ".mp4"


def preset_label(preset: str) -> str:
    return PRESET_LABELS.get(preset, preset.replace("_", " "))


def preset_suffix(preset: str) -> str:
    return PRESET_SUFFIXES.get(preset, DEFAULT_SUFFIX)


_PLATFORM_PRESETS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\byoutube\s*(?:1080p|hd)?\b|\byt\b", re.IGNORECASE), "youtube_1080p"),
    (re.compile(r"\b(?:youtube\s*)?4k\b|\buhd\b", re.IGNORECASE), "youtube_4k"),
    (re.compile(r"\binstagram\s+(?:square|feed|post)\b|\bsquare\b", re.IGNORECASE), "instagram_square"),
    (re.compile(r"\binstagram(?:\s+(?:reels?|stories?))?\b|\breels?\b", re.IGNORECASE), "instagram_reels"),
    (re.compile(r"\btiktok\b|\btik\s*tok\b", re.IGNORECASE), "tiktok"),
    (re.compile(r"\btwitter\b|\bx\.com\b|\bfor\s+x\b", re.IGNORECASE), "twitter_x"),
    (re.compile(r"\bpodcast\b|\baudio\s+only\b|\bmp3\b", re.IGNORECASE), "podcast_audio"),
)


def resolve_preset(text: str) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    lowered = raw.lower().replace("-", "_")
    if lowered in PRESETS:
        return lowered
    explicit = re.search(
        r"\b(youtube_1080p|youtube_4k|instagram_reels|instagram_square|tiktok|twitter_x|podcast_audio)\b",
        raw,
        re.IGNORECASE,
    )
    if explicit:
        return explicit.group(1).lower()
    for pattern, preset in _PLATFORM_PRESETS:
        if pattern.search(raw):
            return preset
    if re.search(r"\b(?:export|render|save)\b", raw, re.IGNORECASE):
        return DEFAULT_PRESET
    return None


def looks_like_export(text: str) -> bool:
    return bool(re.search(r"\b(?:export|render)\b", text or "", re.IGNORECASE))


def exported_path_from_vex_message(message: str) -> str | None:
    text = (message or "").strip()
    if " to " not in text:
        return None
    tail = text.split(" to ", 1)[1]
    tail = tail.split(". Estimated")[0].strip().rstrip(".")
    return tail or None
