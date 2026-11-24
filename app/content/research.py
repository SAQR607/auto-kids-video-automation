"""Research stage (Phase 2, §7): topic claim → fetch → claim↔evidence gate.

Stickman-only: gated by cfg `research.enabled` (Fernwood's config has no such
key, so its pipeline path is untouched). Evidence rules:

- Excerpts are extracted mechanically from the received bytes and capped at
  250 chars — full text lives only in run memory, never on disk.
- Every significant claim needs >= 2 excerpts from >= 2 genuinely independent
  sources (different publisher AND different registrable domain), after
  dropping Wikipedia-derivatives (shingle similarity vs the discovery article)
  and syndicated duplicates (pairwise Jaccard >= 0.8).
- Missing/weak links raise ResearchError → the pipeline checkpoints FAILED +
  Telegram and bounds retries via the attempt budget; the topic is marked
  blocked in the pool record and is never handed to another episode.

All services free: stdlib HTTP + local computation + existing Groq keys.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..config import ROOT
from ..logging_setup import get_logger
from ..state import now_iso

log = get_logger("research")

CLASSES = ("fact", "interpretation", "legend", "myth", "dramatization")
EXCERPT_MAX = 250          # owner spec: <= ~250 chars of supporting sentence(s)
MIN_EXCERPTS = 2           # per claim
MIN_SOURCES = 2            # independent organizations per claim
MIN_SOURCE_CHARS = 200     # below this the fetch was a JS shell / error page
SYNDICATION_JACCARD = 0.8
DERIVATIVE_JACCARD = 0.8
SHINGLE_K = 5
SUPPORT_MIN_OVERLAP = 3    # content words linking a sentence to a claim
FETCH_TIMEOUT_SEC = 20
MAX_SOURCE_BYTES = 1_500_000
MAX_CORPUS_CHARS = 5000    # per source, Groq input only (excerpts use full text)

UA = "Mozilla/5.0 (compatible; StickmanResearch/1.0)"


class ResearchError(RuntimeError):
    """Research blocked (§7) — propagates so the pipeline marks FAILED."""


STOPWORDS = frozenset(
    "a an the and or but if of to in on at by for with from as was were be been "
    "is are this that these those it its into over under about after before "
    "during between through not no nor so than then there here their our your "
    "my he she they we you i his her us them which who whom what when where why "
    "how can could would should will shall may might must have has had do does "
    "did also more most other some any each own same very just very".split()
)

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9']+")


# ---------------- text extraction (mechanical, from received bytes) ----------------

class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return " ".join(" ".join(p.parts).split())


def fetch_url(url: str, *, timeout: float = FETCH_TIMEOUT_SEC) -> str:
    """stdlib HTTP GET → visible text. Raises on non-200 / network errors."""
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — curated pool URLs only
        raw = resp.read(MAX_SOURCE_BYTES)
    return html_to_text(raw.decode("utf-8", "replace"))


def content_words(text: str) -> set[str]:
    return {w for w in _WORD.findall(str(text).lower())
            if len(w) > 3 and w not in STOPWORDS}


def best_excerpt(claim: str, source_text: str, limit: int = EXCERPT_MAX) -> str | None:
    """The source sentence with the highest content-word overlap vs the claim.

    Mechanical: never paraphrased, always a substring of the received text,
    hard-capped at `limit` chars. None when the source does not support it.
    """
    claim_words = content_words(claim)
    best, best_score = None, 0
    for sentence in _SENTENCE.split(source_text):
        sentence = " ".join(sentence.split())
        if not sentence:
            continue
        score = len(claim_words & content_words(sentence))
        if score > best_score:
            best, best_score = sentence, score
    if best is None or best_score < SUPPORT_MIN_OVERLAP:
        return None
    if len(best) > limit:
        cut = best[:limit]
        best = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return best


# ---------------- independence (§7) ----------------

_MULTI_TLDS = ("co.uk", "org.uk", "ac.uk", "com.au", "co.nz", "com.br")


def registrable_domain(url: str) -> str:
    # shortcut: last-labels heuristic (no public-suffix list); good enough for
    # the curated pool — upgrade when an unseen multi-part TLD shows up.
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if ".".join(labels[-2:]) in _MULTI_TLDS:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def independent(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Genuine independence: different publishing organization AND different
    registrable domain (subdomains/mirrors/editions do not count)."""
    return (str(a.get("publisher", "")).lower() != str(b.get("publisher", "")).lower()
            and registrable_domain(str(a.get("url", ""))) != registrable_domain(str(b.get("url", ""))))


def shingles(text: str, k: int = SHINGLE_K) -> set[str]:
    words = _WORD.findall(str(text).lower())
    if len(words) >= k:
        return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}
    return {" ".join(words)} if words else set()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _evidence_entry(doc: dict[str, Any], excerpt: str) -> dict[str, Any]:
    return {"url": doc["url"], "title": doc.get("title", ""),
            "publisher": doc.get("publisher", ""), "access_date": now_iso()[:10],
            "excerpt": excerpt}


def supporting_evidence(claim: str, docs: list[dict[str, Any]],
                        discovery_text: str | None = None) -> list[dict[str, Any]]:
    """<=2 entries from >=2 independent sources, or [] when the claim is weak.

    Order: mechanical excerpt per source → drop Wikipedia-derivatives → drop
    syndicated duplicates (keep the first/curated-best) → require an
    independent pair.
    """
    hits = [(d, ex) for d in docs if (ex := best_excerpt(claim, d.get("text", "")))]
    if discovery_text:
        disc = shingles(discovery_text)
        kept = [(d, ex) for d, ex in hits
                if jaccard(shingles(d.get("text", "")), disc) < DERIVATIVE_JACCARD]
        if len(kept) != len(hits):
            log.info("research: dropped %d Wikipedia-derivative source(s) for claim %r",
                     len(hits) - len(kept), claim[:60])
        hits = kept
    unique: list[tuple[dict[str, Any], str]] = []
    for d, ex in hits:
        if any(jaccard(shingles(d.get("text", "")), shingles(u.get("text", "")))
               >= SYNDICATION_JACCARD for u, _ in unique):
            log.info("research: dropped syndicated duplicate %s for claim %r",
                     d.get("url"), claim[:60])
            continue
        unique.append((d, ex))
    for i in range(len(unique)):
        for j in range(i + 1, len(unique)):
            if independent(unique[i][0], unique[j][0]):
                return [_evidence_entry(*unique[i]), _evidence_entry(*unique[j])]
    return []


# ---------------- claim extraction (Groq summarizes only from fetched text) ----------------

def claim_messages(topic: dict[str, Any], docs: list[dict[str, Any]]) -> list[dict[str, str]]:
    corpus = "\n\n".join(
        f"SOURCE {i}: {d.get('title', '')} ({d.get('publisher', '')}) {d['url']}\n"
        f"{d.get('text', '')[:MAX_CORPUS_CHARS]}"
        for i, d in enumerate(docs, 1)
    )
    user = f"""Extract the significant factual claims from the SOURCE texts below, for a short
history video about: {topic.get('title', '')} — {topic.get('brief', '')}

Rules:
- Use ONLY what the sources state; never add outside knowledge.
- Keep only significant claims a viewer would hear stated as true (typically 4-8).
- Each claim: one short standalone sentence; class exactly one of {list(CLASSES)}.
Return minified JSON: {{"claims":[{{"claim":"...","class":"fact"}}]}}"""

    return [
        {"role": "system", "content":
         "You extract checkable factual claims from provided source text only. "
         "Output a single minified JSON object. No markdown, no commentary."},
        {"role": "user", "content": user + "\n\n" + corpus},
    ]


def validate_claims(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["output must be a JSON object"]
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["claims must be a non-empty list"]
    errors: list[str] = []
    for i, c in enumerate(claims):
        if not isinstance(c, dict):
            errors.append(f"claims[{i}] must be an object")
            continue
        if not str(c.get("claim") or "").strip():
            errors.append(f"claims[{i}].claim is empty")
        if c.get("class") not in CLASSES:
            errors.append(f"claims[{i}].class must be one of {list(CLASSES)}")
    return errors


# ---------------- topic pool + record (rotation, no duplicates) ----------------

def _read_json(path_str: str) -> Any:
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8"))


def _atomic_write(path: Path, data: Any) -> None:
    from .engine import _atomic_write_json  # lazy: engine imports this module at stage run

    _atomic_write_json(path, data)


def _load_pool(cfg: Any) -> dict[str, Any]:
    path = str(cfg.get("research.pool_path", "topics/pool.json"))
    try:
        raw = _read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchError(f"topic pool unreadable ({path}): {type(exc).__name__}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("topics"), list) or not raw["topics"]:
        raise ResearchError(f"topic pool missing or empty: {path}")
    return raw


def claim_topic(pool: dict[str, Any], record: dict[str, Any], episode_id: str) -> dict[str, Any]:
    """Rotation: an episode keeps its own topic across retries; recorded topics
    (used/blocked/pending) are never handed to another episode."""
    topics = pool["topics"]
    recs = record.setdefault("topics", {})
    for t in topics:
        if recs.get(str(t.get("id")), {}).get("episode_id") == episode_id:
            return t
    for t in topics:
        tid = str(t.get("id"))
        if tid not in recs:
            recs[tid] = {"status": "pending", "episode_id": episode_id,
                         "updated_at": now_iso()}
            return t
    raise ResearchError("topic pool exhausted: every topic is used or blocked")


def _save_record(cfg: Any, record: dict[str, Any], episode_id: str, topic_id: str,
                 *, status: str, error: str | None = None) -> None:
    rec = record.setdefault("topics", {}).setdefault(topic_id, {})
    rec.update({"status": status, "episode_id": episode_id, "updated_at": now_iso()})
    if error:
        rec["error"] = error[:300]
    elif status == "used":
        rec.pop("error", None)
    _atomic_write(Path(str(cfg.get("research.record_path", "topics/record.json"))), record)


# ---------------- stage ----------------

def _fetch_sources(topic: dict[str, Any], *, fetch: Callable[[str], str]
                   ) -> tuple[list[dict[str, Any]], str | None]:
    docs: list[dict[str, Any]] = []
    discovery: str | None = None
    disc = topic.get("discovery") or {}
    if disc.get("url"):
        try:
            discovery = fetch(str(disc["url"]))
        except Exception as exc:  # discovery is auxiliary — never fatal alone
            log.warning("research: discovery fetch failed (%s): %s",
                        disc["url"], type(exc).__name__)
    for s in topic.get("sources", []):
        try:
            text = fetch(str(s["url"]))
        except Exception as exc:
            log.warning("research: source fetch failed (%s): %s — %d/%d usable so far",
                        s.get("url"), type(exc).__name__, len(docs),
                        int(MIN_SOURCES))
            continue
        if len(text) < MIN_SOURCE_CHARS:
            log.warning("research: source too short (%d chars, likely a JS shell): %s",
                        len(text), s.get("url"))
            continue
        docs.append({**s, "text": text})
    return docs, discovery


def _research_for(episode_id: str, topic: dict[str, Any], *,
                  generate: Callable[..., dict[str, Any]],
                  fetch: Callable[[str], str]) -> dict[str, Any]:
    docs, discovery = _fetch_sources(topic, fetch=fetch)
    if len(docs) < MIN_SOURCES:
        raise ResearchError(
            f"topic {topic.get('id')}: only {len(docs)} usable source(s), need {MIN_SOURCES}")
    claims = generate(claim_messages(topic, docs), validate_claims,
                      "research_claims", 2500)["claims"]
    out: list[dict[str, Any]] = []
    for c in claims:
        claim = str(c["claim"])
        evidence = supporting_evidence(claim, docs, discovery)
        if len(evidence) < MIN_EXCERPTS:
            raise ResearchError(
                f"claim lacks {MIN_EXCERPTS} excerpts from {MIN_SOURCES} independent "
                f"sources ({len(evidence)} found): {claim[:120]!r}")
        out.append({"claim": claim, "class": c["class"], "evidence": evidence})
    return {"schema": "stickman.research/1", "episode_id": episode_id,
            "topic_id": topic.get("id"), "topic_title": topic.get("title"),
            "access_date": now_iso()[:10], "claims": out,
            "sources": [{"url": d["url"], "title": d.get("title", ""),
                         "publisher": d.get("publisher", "")} for d in docs]}


def run_research(cfg: Any, episode_id: str, *,
                 generate: Callable[..., dict[str, Any]],
                 fetch: Callable[[str], str] | None = None) -> dict[str, Any] | None:
    """Stage hook (engine, SCRIPTED): returns the research dict, or None when
    research is disabled (Fernwood). Raises ResearchError when blocked."""
    if not cfg.get("research.enabled"):
        return None
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    path = base / "research.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        log.info("%s: research.json present (%d claims) — skipping research",
                 episode_id, len(cached.get("claims", [])))
        return cached

    pool = _load_pool(cfg)
    record_path = str(cfg.get("research.record_path", "topics/record.json"))
    try:
        record = _read_json(record_path)
    except (OSError, json.JSONDecodeError):
        record = {}
    if not isinstance(record, dict):
        record = {}

    topic = claim_topic(pool, record, episode_id)
    _save_record(cfg, record, episode_id, str(topic.get("id")), status="pending")

    if fetch is None:
        timeout = float(cfg.get("research.fetch_timeout_sec", FETCH_TIMEOUT_SEC))
        fetch = lambda u: fetch_url(u, timeout=timeout)  # noqa: E731
    try:
        research = _research_for(episode_id, topic, generate=generate, fetch=fetch)
    except ResearchError as exc:
        _save_record(cfg, record, episode_id, str(topic.get("id")),
                     status="blocked", error=str(exc))
        log.error("%s: research BLOCKED on topic %s: %s",
                  episode_id, topic.get("id"), exc)
        raise
    _atomic_write(path, research)
    _save_record(cfg, record, episode_id, str(topic.get("id")), status="used")
    log.info("%s: research ok — topic %s, %d claim(s), %d source(s)",
             episode_id, topic.get("id"), len(research["claims"]),
             len(research["sources"]))
    return research
