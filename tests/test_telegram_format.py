"""Telegram message formatter tests (§36/§39)."""

from datetime import datetime, timezone

from app.telegram_client import (format_alert, format_stats, format_success_long,
                                 format_success_shorts)


def test_success_long_format():
    msg = format_success_long("s01e001", "A Shimmering Surprise", "vid123",
                              "public", "PASS", "PASS")
    assert "Long video published" in msg
    assert "🎬 A Shimmering Surprise" in msg
    assert "vid123" in msg and "https://youtu.be/vid123" in msg
    assert "public" in msg and "script PASS" in msg and "video PASS" in msg


def test_success_shorts_format_links_each_short():
    msg = format_success_shorts("s01e001", ["vidA", "vidB"], 2)
    assert "Shorts published" in msg
    assert "Uploaded: 2/2" in msg
    assert "1️⃣ https://youtu.be/vidA" in msg
    assert "2️⃣ https://youtu.be/vidB" in msg


def test_success_shorts_format_partial():
    msg = format_success_shorts("s01e001", ["vidA"], 2)
    assert "Uploaded: 1/2" in msg
    assert "vidB" not in msg


def test_stats_format_totals_and_next_shorts():
    nxt = {"kind": "shorts", "at": datetime(2026, 10, 6, 16, 0, tzinfo=timezone.utc),
           "remaining_sec": 23 * 3600, "count": 2, "episode_ids": ["s01e001"]}
    msg = format_stats({"longs": 1, "shorts": 0, "total": 1}, nxt)
    assert "📊 Channel Stats" in msg
    assert "Total videos: 1" in msg
    assert "Long: 1" in msg and "Shorts: 0" in msg
    assert "Shorts ×2 — s01e001" in msg
    assert "23h 0m" in msg and "UTC" in msg


def test_stats_format_next_long_with_planned_episode():
    nxt = {"kind": "long", "at": datetime(2026, 10, 14, 16, 0, tzinfo=timezone.utc),
           "remaining_sec": 86400, "count": 1, "episode_ids": ["s01e002"]}
    msg = format_stats({"longs": 1, "shorts": 2, "total": 3}, nxt)
    assert "Total videos: 3" in msg
    assert "Long — s01e002" in msg
    assert "1d 0h" in msg


def test_stats_format_none_pending():
    msg = format_stats({"longs": 0, "shorts": 0, "total": 0}, None)
    assert "Total videos: 0" in msg
    assert "none scheduled" in msg


def test_alert_format():
    msg = format_alert("s01e001", "RENDER_QC", "boom", 1, 3)
    assert "RED ALERT" in msg
    assert "episode: s01e001" in msg
    assert "stage: RENDER_QC" in msg
    assert "error: boom" in msg
    assert "attempts: 1/3" in msg


def test_alert_format_without_max():
    msg = format_alert("-", "UPLOADING", "quota", 2)
    assert "attempts: 2" in msg and "1/3" not in msg
