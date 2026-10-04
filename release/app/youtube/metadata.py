"""Video metadata bodies for videos.insert (§48).

Kids-safety: every upload sets selfDeclaredMadeForKids=True; privacy is
private for tests, public for real runs. Titles/descriptions/tags come from
the QC-passed package (§15 enforces the content rules).
"""

from __future__ import annotations

from typing import Any

# Film & Animation — config-overridable via youtube.category_id.
DEFAULT_CATEGORY = "1"

YT_TITLE_MAX = 100
YT_DESC_MAX = 5000
YT_TAGS_MAX = 30
YT_TAGS_CHARS = 450  # API total limit is 500; keep headroom


def privacy_status(private: bool) -> str:
    return "private" if private else "public"


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def long_body(package: dict[str, Any], *, private: bool,
              category_id: str = DEFAULT_CATEGORY) -> dict:
    meta = package.get("metadata", {})
    tags = [str(t) for t in meta.get("tags", [])][:YT_TAGS_MAX]
    # keep the API's aggregate tags length under the limit
    kept: list[str] = []
    used = 0
    for t in tags:
        if used + len(t) + 1 > YT_TAGS_CHARS:
            break
        kept.append(t)
        used += len(t) + 1
    return {
        "snippet": {
            "title": _clip(str(meta.get("title") or package.get("title") or "Fernwood Friends"), YT_TITLE_MAX),
            "description": _clip(str(meta.get("description") or ""), YT_DESC_MAX),
            "tags": kept,
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy_status(private),
            "selfDeclaredMadeForKids": True,
        },
    }


def short_body(short_doc: dict[str, Any], *, private: bool,
               long_title: str = "", category_id: str = DEFAULT_CATEGORY) -> dict:
    title = _clip(f"{short_doc.get('title', 'Fernwood Friends Short')} | Fernwood Friends", YT_TITLE_MAX)
    lines = [
        str(short_doc.get("title", "")) + " — a Fernwood Friends short for ages 4-8.",
    ]
    if long_title:
        lines.append(f"Full story: {long_title}")
    lines.append("#shorts")
    return {
        "snippet": {
            "title": title,
            "description": _clip("\n".join(lines), YT_DESC_MAX),
            "tags": ["kids stories", "shorts", "woodland animals", "ages 4-8",
                     "animated stories for kids", "preschool stories"],
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy_status(private),
            "selfDeclaredMadeForKids": True,
        },
    }
