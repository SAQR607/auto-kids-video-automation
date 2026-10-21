"""Video metadata bodies for videos.insert (§48) + growth layer.

Kids-safety: made-for-kids flag comes from channel.made_for_kids (default
True); privacy is private for tests, public for real runs. Titles/descriptions/
tags come from the QC-passed package (§15 enforces the content rules); this
layer merges the static core keyword bank with the per-episode tags and
assembles the final search-optimized description (keyword head + episode
summary + hashtags). No links, no engagement bait (§7 of
docs/YOUTUBE_GROWTH.md — COPPA rules).

Every bank is config-overridable (profile support): absent keys fall back to
the Fernwood defaults below, so the default profile behaves identically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import Config

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


def _cfg_get(cfg: "Config | None", dotted: str) -> Any:
    return cfg.get(dotted) if cfg is not None else None


def brand(cfg: "Config | None" = None) -> str:
    return str(_cfg_get(cfg, "channel.name") or "Fernwood Friends")


def made_for_kids(cfg: "Config | None" = None) -> bool:
    val = _cfg_get(cfg, "channel.made_for_kids")
    return True if val is None else bool(val)


def core_tags(cfg: "Config | None" = None) -> list[str]:
    return [str(t) for t in (_cfg_get(cfg, "youtube.core_tags") or CORE_TAGS)]


def core_tag_lead(cfg: "Config | None" = None) -> int:
    val = _cfg_get(cfg, "youtube.core_tag_lead")
    return CORE_TAG_LEAD if val is None else int(val)


def description_head(cfg: "Config | None" = None) -> str:
    return str(_cfg_get(cfg, "youtube.description_head") or DESCRIPTION_HEAD)


def shorts_head(cfg: "Config | None" = None) -> str:
    return str(_cfg_get(cfg, "youtube.shorts_head") or SHORTS_HEAD)


def hashtags(cfg: "Config | None" = None) -> str:
    return str(_cfg_get(cfg, "youtube.hashtags") or HASHTAGS)


def shorts_tags(cfg: "Config | None" = None) -> list[str]:
    return [str(t) for t in (_cfg_get(cfg, "youtube.shorts_tags") or SHORTS_TAGS)]


def short_keyword_phrase(cfg: "Config | None" = None) -> str:
    return str(_cfg_get(cfg, "youtube.short_keyword_phrase") or "Bedtime Story for Kids")


def audience_suffix(cfg: "Config | None" = None) -> str:
    val = _cfg_get(cfg, "channel.audience_suffix")
    if val is None:
        return " for ages 4-8"
    return str(val)


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


def _long_description(meta: dict[str, Any], cfg: "Config | None") -> str:
    body = str(meta.get("description") or "").strip()
    head = description_head(cfg)
    tags_text = hashtags(cfg)
    return _clip(f"{head}\n\n{body}\n\n{tags_text}", YT_DESC_MAX)


def long_body(package: dict[str, Any], *, private: bool,
              category_id: str = DEFAULT_CATEGORY,
              cfg: "Config | None" = None) -> dict:
    meta = package.get("metadata", {})
    core = core_tags(cfg)
    lead = core_tag_lead(cfg)
    dynamic = [str(t) for t in meta.get("tags", [])][:YT_TAGS_MAX]
    tags = _cap_tags(_merge_tags(core[:lead], dynamic, core[lead:]))
    return {
        "snippet": {
            "title": _clip(str(meta.get("title") or package.get("title") or brand(cfg)), YT_TITLE_MAX),
            "description": _long_description(meta, cfg),
            "tags": tags,
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy_status(private),
            "selfDeclaredMadeForKids": made_for_kids(cfg),
        },
    }


def short_body(short_doc: dict[str, Any], *, private: bool,
               long_title: str = "", category_id: str = DEFAULT_CATEGORY,
               tags: list[str] | None = None,
               cfg: "Config | None" = None) -> dict:
    name = brand(cfg)
    keyword_phrase = short_keyword_phrase(cfg)
    title = _clip(
        f"{short_doc.get('title', name)} | {keyword_phrase} | {name}",
        YT_TITLE_MAX,
    )
    lines = [
        str(short_doc.get("title", "")) + f" — a {name} short{audience_suffix(cfg)}.",
    ]
    quote = next((str(d.get("text", "")).strip()
                  for d in short_doc.get("dialogue", [])
                  if isinstance(d, dict) and str(d.get("text", "")).strip()), "")
    if quote:
        lines.append(f"“{quote}”")
    if long_title:
        lines.append(f"Full story: {long_title}")
    lines.append("")
    lines.append(shorts_head(cfg))
    lines.append("")
    lines.append(f"#shorts {hashtags(cfg)}")
    core = core_tags(cfg)
    lead = core_tag_lead(cfg)
    merged = _merge_tags(core[:lead], shorts_tags(cfg),
                         [str(t) for t in (tags or [])][:YT_TAGS_MAX],
                         core[lead:])
    return {
        "snippet": {
            "title": title,
            "description": _clip("\n".join(lines), YT_DESC_MAX),
            "tags": _cap_tags(merged),
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy_status(private),
            "selfDeclaredMadeForKids": made_for_kids(cfg),
        },
    }
