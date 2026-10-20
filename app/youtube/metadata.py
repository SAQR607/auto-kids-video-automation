"""Video metadata bodies for videos.insert (§48) + growth layer.

Kids-safety: every upload sets selfDeclaredMadeForKids=True; privacy is
private for tests, public for real runs. Titles/descriptions/tags come from
the QC-passed package (§15 enforces the content rules); this layer merges the
static core keyword bank with the per-episode tags and assembles the final
search-optimized description (keyword head + episode summary + hashtags).
No links, no engagement bait (§7 of docs/YOUTUBE_GROWTH.md — COPPA rules).
"""

from __future__ import annotations

from typing import Any

# Film & Animation — config-overridable via youtube.category_id.
DEFAULT_CATEGORY = "1"

YT_TITLE_MAX = 100
YT_DESC_MAX = 5000
YT_TAGS_MAX = 30
YT_TAGS_CHARS = 450  # API total limit is 500; keep headroom

# Static core bank — high-volume US-English parent search terms, ordered most
# valuable first (docs/YOUTUBE_GROWTH.md §4.2 + vidIQ demand data Oct 2026:
# 151k / 48k / 4.6k monthly searches for the top three phrases). Package tags
# are merged after the priority lead; dedupe is case-insensitive.
CORE_TAGS = [
    "bedtime stories for kids",
    "bedtime stories for toddlers",
    "calming bedtime stories for kids with relaxing music",
    "animated stories for kids",
    "fernwood friends",
    "preschool stories",
    "kids stories",
    "gentle stories for kids",
    "stories for kids",
    "kids animation",
    "wholesome kids video",
    "calming bedtime story",
    "kids cartoon",
    "ages 4-8",
    "woodland animals",
    "friendship stories for kids",
]
CORE_TAG_LEAD = 6  # always-first subset so the money phrases never get cut

# Keyword head — first ~150 chars of every long description (search gold).
DESCRIPTION_HEAD = (
    "Gentle bedtime stories for kids ages 4-8 — animated woodland adventures "
    "about friendship and kindness, made for preschool viewers."
)

SHORTS_HEAD = (
    "Gentle bedtime stories for kids — more woodland adventures with "
    "Fernwood Friends."
)

HASHTAGS = "#FernwoodFriends #BedtimeStoriesForKids #AnimatedStoriesForKids #KidsStories"
SHORTS_TAGS = ["shorts", "short videos for kids", "kids short stories"]


def privacy_status(private: bool) -> str:
    return "private" if private else "public"


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _merge_tags(*groups: list[str]) -> list[str]:
    """Concatenate tag groups, dropping empties and case-insensitive dupes."""
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for raw in group:
            tag = str(raw).strip()
            key = tag.lower()
            if not tag or key in seen:
                continue
            seen.add(key)
            out.append(tag)
    return out


def _cap_tags(tags: list[str]) -> list[str]:
    """Apply the API's count + aggregate-char limits, preserving order."""
    kept: list[str] = []
    used = 0
    for t in tags[:YT_TAGS_MAX]:
        if used + len(t) + 1 > YT_TAGS_CHARS:
            break
        kept.append(t)
        used += len(t) + 1
    return kept


def _long_description(meta: dict[str, Any]) -> str:
    body = str(meta.get("description") or "").strip()
    return _clip(f"{DESCRIPTION_HEAD}\n\n{body}\n\n{HASHTAGS}", YT_DESC_MAX)


def long_body(package: dict[str, Any], *, private: bool,
              category_id: str = DEFAULT_CATEGORY) -> dict:
    meta = package.get("metadata", {})
    dynamic = [str(t) for t in meta.get("tags", [])][:YT_TAGS_MAX]
    tags = _cap_tags(_merge_tags(CORE_TAGS[:CORE_TAG_LEAD], dynamic,
                                 CORE_TAGS[CORE_TAG_LEAD:]))
    return {
        "snippet": {
            "title": _clip(str(meta.get("title") or package.get("title") or "Fernwood Friends"), YT_TITLE_MAX),
            "description": _long_description(meta),
            "tags": tags,
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy_status(private),
            "selfDeclaredMadeForKids": True,
        },
    }


def short_body(short_doc: dict[str, Any], *, private: bool,
               long_title: str = "", category_id: str = DEFAULT_CATEGORY,
               tags: list[str] | None = None) -> dict:
    keyword_phrase = "Bedtime Story for Kids"
    title = _clip(
        f"{short_doc.get('title', 'Fernwood Friends Short')} | {keyword_phrase} | Fernwood Friends",
        YT_TITLE_MAX,
    )
    lines = [
        str(short_doc.get("title", "")) + " — a Fernwood Friends short for ages 4-8.",
    ]
    quote = next((str(d.get("text", "")).strip()
                  for d in short_doc.get("dialogue", [])
                  if isinstance(d, dict) and str(d.get("text", "")).strip()), "")
    if quote:
        lines.append(f"“{quote}”")
    if long_title:
        lines.append(f"Full story: {long_title}")
    lines.append("")
    lines.append(SHORTS_HEAD)
    lines.append("")
    lines.append(f"#shorts {HASHTAGS}")
    merged = _merge_tags(CORE_TAGS[:CORE_TAG_LEAD], SHORTS_TAGS,
                         [str(t) for t in (tags or [])][:YT_TAGS_MAX],
                         CORE_TAGS[CORE_TAG_LEAD:])
    return {
        "snippet": {
            "title": title,
            "description": _clip("\n".join(lines), YT_DESC_MAX),
            "tags": _cap_tags(merged),
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy_status(private),
            "selfDeclaredMadeForKids": True,
        },
    }
