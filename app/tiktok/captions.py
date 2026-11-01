"""TikTok-native captions for shorts (parent-directed, follow not subscribe).

Short, keyword-dense captions in TikTok's style: hook title, one parent
sentence, a tight hashtag block (broad + niche). No engagement bait toward
kids — the follow line addresses grown-ups, matching the channel's stance.
"""

from __future__ import annotations

from typing import Any

TITLE_MAX = 90
DESC_MAX = 2200

FOLLOW_LINE = "Grown-ups: follow for more gentle bedtime stories for little ones."
HASHTAGS = "#bedtimestories #forkids #kidsanimation #preschool #woodlandstories #fernwoodfriends"


def build_title(doc: dict[str, Any], episode_id: str) -> str:
    """Short title: hook + brand, capped for TikTok's title field."""
    hook = str(doc.get("title") or "A gentle meadow moment").strip()
    title = f"{hook} | Fernwood Friends"
    if len(title) > TITLE_MAX:
        title = hook[: TITLE_MAX - 1].rstrip() + "…"
    tag = episode_id.upper().replace("S0", "S")
    return f"{title} {tag}"[:TITLE_MAX]


def build_description(doc: dict[str, Any], episode_id: str) -> str:
    """Hook + parent follow line + hashtags (well under TikTok's limit)."""
    hook = str(doc.get("title") or "A gentle woodland moment").strip().rstrip(".")
    kind = str(doc.get("kind") or "story")
    chars = [c.capitalize() for c in (doc.get("characters") or []) if isinstance(c, str)]
    who = " and ".join(chars[:3]) if chars else "the Fernwood friends"
    body = (
        f"{hook}. \U0001F33F\n\n"
        f"A gentle {kind} moment with {who}.\n\n"
        f"{FOLLOW_LINE}\n\n"
        f"{HASHTAGS}\n{episode_id}"
    )
    return body[:DESC_MAX]
