"""Prompt-brief regression guards: the s01e004 failure modes (Oct 2026).

That run invented an 'endcard' music mood + solo end-card scene 14, underwrote
words (1095 < 1100 floor), and leaked arc words into a short. The brief must
keep saying the opposite.
"""

from __future__ import annotations

from app.content.prompts import SCRIPT_BRIEF
from app.content.universe import BEAT_TEMPLATE


def test_beat_template_final_beat_is_normal_scene():
    assert "farewell wave" in BEAT_TEMPLATE
    assert "end-card" not in BEAT_TEMPLATE
    assert "2-4 friends on screen" in BEAT_TEMPLATE
    assert "EXACTLY 14 scenes" in BEAT_TEMPLATE


def test_brief_sc14_is_normal_scene_not_end_card():
    assert "NORMAL full scene" in SCRIPT_BRIEF
    assert "NOT a solo end card" in SCRIPT_BRIEF
    assert "2-4 characters on screen" in SCRIPT_BRIEF


def test_brief_music_mood_closed_list_and_examples():
    assert "never invent" in SCRIPT_BRIEF
    assert "'endcard'" in SCRIPT_BRIEF  # named as invalid so the model avoids it


def test_brief_word_floor_aim():
    assert "~1260 total" in SCRIPT_BRIEF
    assert "under ~1150 words are rejected" in SCRIPT_BRIEF


def test_brief_shorts_arc_word_ban_listed():
    assert "cave, compass, heart stone, root door or pebble stack" in SCRIPT_BRIEF


def test_repair_messages_truncates_huge_previous_output():
    from app.content.prompts import repair_messages

    huge = "x" * 20000
    msgs = repair_messages("script", ["title too long"], huge,
                           [{"role": "user", "content": "base"}])
    prev = msgs[-2]["content"]
    assert len(prev) < 4500  # repair prompt must stay under the 8000 TPM
    assert "[middle truncated" in prev
    assert "title too long" in msgs[-1]["content"]


def test_repair_messages_keeps_small_previous_verbatim():
    from app.content.prompts import repair_messages

    msgs = repair_messages("premise", [], "tiny output", [])
    assert msgs[-2]["content"] == "tiny output"
