from __future__ import annotations

from vex_desktop.ui.thumbs import extract_thumbnails, parse_ffmpeg_duration, video_duration_ms


def test_extract_thumbnails_from_sample(sample_video):
    frames = extract_thumbnails(sample_video, count=4, width=96)
    assert len(frames) >= 1
    for ms, image in frames:
        assert ms >= 0
        assert not image.isNull()
        assert image.width() > 0
        assert image.height() > 0


def test_sample_video_has_duration(sample_video):
    duration = video_duration_ms(sample_video)
    assert duration is not None
    assert duration >= 500


def test_parse_ffmpeg_duration_line():
    assert parse_ffmpeg_duration("Duration: 00:00:01.00, start: 0.000000") == 1000
    assert parse_ffmpeg_duration("nope") is None


def test_audio_suffix_skips_thumbs(tmp_path):
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"not a video")
    assert extract_thumbnails(audio) == []


def test_missing_file_skips_thumbs(tmp_path):
    assert extract_thumbnails(tmp_path / "missing.mp4") == []


def test_missing_ffmpeg_skips_thumbs(sample_video, monkeypatch):
    monkeypatch.setattr("vex_desktop.ui.thumbs.ffmpeg_path", lambda: None)
    assert extract_thumbnails(sample_video) == []
