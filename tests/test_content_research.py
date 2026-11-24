"""Research stage (plan §7): topic rotation/no-duplicates, excerpt rules,
independence (publisher / Wikipedia-derivative / syndication), claim↔evidence
blocking, retry semantics, and Fernwood staying research-free.

All offline: fetch and Groq are faked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import Config, validate_config
from app.content.research import (
    EXCERPT_MAX,
    ResearchError,
    best_excerpt,
    claim_topic,
    independent,
    registrable_domain,
    run_research,
    supporting_evidence,
    validate_claims,
)
from app.qc.script_qc import collect_script_errors

CLAIM = "The Olympic Games were held every four years at Olympia in Greece."

WIKI = ("The Olympic Games were a festival held at Olympia in Greece. "
        "Ancient Greeks gathered every four years for the games.")
SRC_A = ("Ancient Greeks gathered at Olympia for the Olympic Games, which were "
         "held every four years across many centuries of Greek history. "
         "Runners, wrestlers and chariot racers competed before crowds who "
         "travelled from far-off city-states to watch the contests.")
SRC_B = ("From 776 BC the games recurred every four years, a rhythm the Greeks "
         "kept faithfully at Olympia in Greece. Victors received olive wreaths, "
         "and truces were declared so travellers could reach the sanctuary.")
SRC_C = ("Pottery shards and market stalls lined the ancient harbour, where "
         "merchants haggled over cloth and grain through the busy afternoon "
         "hours. Nothing about festivals or athletics appeared in these quiet "
         "records of daily trade along the waterfront.")

DOC_A = {"url": "https://a.example/olympics", "title": "A", "publisher": "Org A"}
DOC_B = {"url": "https://b.example/olympics", "title": "B", "publisher": "Org B"}


def _topic(sources=None, tid="olympic_games"):
    return {"id": tid, "title": "The Ancient Olympic Games",
            "brief": "how the games began",
            "discovery": {"url": "https://en.wikipedia.org/wiki/Olympic_Games",
                          "title": "Olympic Games", "publisher": "Wikipedia"},
            "sources": sources or [DOC_A, DOC_B]}


def _pool(*topics):
    return {"topics": [dict(t) for t in topics]}


def _cfg(tmp_path, **research):
    data = {"paths": {"state": str(tmp_path / "state")},
            "research": {"enabled": True,
                         "pool_path": str(tmp_path / "pool.json"),
                         "record_path": str(tmp_path / "record.json"),
                         "fetch_timeout_sec": 1, **research}}
    return Config(data=data, path=Path("config/config.example.json"))


def _write_pool(tmp_path, *topics):
    (tmp_path / "pool.json").write_text(json.dumps(_pool(*topics)), encoding="utf-8")


def _fetch(mapping):
    def fetch(url):
        value = mapping[url]
        if isinstance(value, Exception):
            raise value
        return value
    return fetch


def _generate(claims=None):
    """Fake Groq stage: returns claims, after running the real validator."""
    def generate(messages, validator, stage, max_tokens):
        data = {"claims": claims if claims is not None
                else [{"claim": CLAIM, "class": "fact"}]}
        errors = validator(data)
        assert not errors, errors
        return data
    return generate


def _map(**overrides):
    mapping = {"https://en.wikipedia.org/wiki/Olympic_Games": WIKI,
               "https://a.example/olympics": SRC_A,
               "https://b.example/olympics": SRC_B}
    mapping.update(overrides)
    return mapping


# --- happy path -------------------------------------------------------------


def test_research_writes_evidence_and_marks_topic_used(tmp_path):
    cfg = _cfg(tmp_path)
    _write_pool(tmp_path, _topic())
    res = run_research(cfg, "s01e002", generate=_generate(), fetch=_fetch(_map()))

    claim = res["claims"][0]
    assert claim["class"] == "fact"
    assert len(claim["evidence"]) == 2  # 2 excerpts
    publishers = {e["publisher"] for e in claim["evidence"]}
    assert publishers == {"Org A", "Org B"}  # 2 independent sources
    for e in claim["evidence"]:
        assert len(e["excerpt"]) <= EXCERPT_MAX
        assert e["access_date"]
        assert e["url"] in (DOC_A["url"], DOC_B["url"])

    saved = json.loads(
        (tmp_path / "state" / "episodes" / "s01e002" / "research.json").read_text(encoding="utf-8"))
    assert saved["topic_id"] == "olympic_games"
    assert saved["claims"] == res["claims"]
    # full source text never lands in the artifact
    assert "harbour" not in json.dumps(saved)

    record = json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))
    assert record["topics"]["olympic_games"]["status"] == "used"


def test_research_is_idempotent_from_artifact(tmp_path):
    cfg = _cfg(tmp_path)
    _write_pool(tmp_path, _topic())
    run_research(cfg, "s01e002", generate=_generate(), fetch=_fetch(_map()))

    def boom(url):
        raise AssertionError("must not fetch again when research.json exists")
    cached = run_research(cfg, "s01e002", generate=lambda *a: boom(None), fetch=boom)
    assert cached["claims"][0]["claim"] == CLAIM


# --- blocking ---------------------------------------------------------------


def test_missing_link_blocks_and_marks_topic_blocked(tmp_path):
    cfg = _cfg(tmp_path)
    _write_pool(tmp_path, _topic(), _topic(tid="colosseum"))
    bad = _fetch(_map(**{"https://b.example/olympics": SRC_C}))

    with pytest.raises(ResearchError, match="independent"):
        run_research(cfg, "s01e002", generate=_generate(), fetch=bad)

    record = json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))
    assert record["topics"]["olympic_games"]["status"] == "blocked"
    assert "independent" in record["topics"]["olympic_games"]["error"]
    assert not (tmp_path / "state" / "episodes" / "s01e002" / "research.json").exists()

    # rotation: the blocked topic is never handed to another episode
    assert claim_topic(json.loads((tmp_path / "pool.json").read_text(encoding="utf-8")),
                       record, "s01e003")["id"] == "colosseum"


def test_same_episode_retry_reclaims_its_own_topic(tmp_path):
    cfg = _cfg(tmp_path)
    _write_pool(tmp_path, _topic())
    with pytest.raises(ResearchError):
        run_research(cfg, "s01e002", generate=_generate(),
                     fetch=_fetch(_map(**{"https://b.example/olympics": SRC_C})))
    # retry (next pipeline attempt) succeeds on the same topic — not "exhausted"
    res = run_research(cfg, "s01e002", generate=_generate(), fetch=_fetch(_map()))
    assert res["claims"]
    record = json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))
    assert record["topics"]["olympic_games"]["status"] == "used"


def test_unusable_sources_block_below_minimum(tmp_path):
    cfg = _cfg(tmp_path)
    _write_pool(tmp_path, _topic())
    with pytest.raises(ResearchError, match="usable source"):
        run_research(cfg, "s01e002", generate=_generate(),
                     fetch=_fetch({"https://en.wikipedia.org/wiki/Olympic_Games":
                                   RuntimeError("403"),
                                   "https://a.example/olympics": RuntimeError("403"),
                                   "https://b.example/olympics": RuntimeError("403")}))


def test_research_block_flows_into_failed_and_attempt_budget(tmp_path, monkeypatch):
    """ResearchError must use the generic §33 path: FAILED + attempts+1."""
    from app import pipeline
    from app.state import Stage, load_registry

    cfg = Config(data={"telegram": {"notify_failure": False}}, path=__file__)
    reg = load_registry(tmp_path / "state")
    ep_id = reg.episode_id_for_slot("slot")
    reg.get(ep_id)["stage"] = Stage.SCRIPTED.value
    reg.save()

    def boom(*args, **kwargs):
        raise ResearchError("claim lacks 2 excerpts from 2 independent sources")

    monkeypatch.setattr(pipeline, "_call", boom)
    with pytest.raises(SystemExit):
        pipeline._execute_stage(cfg, reg, ep_id, Stage.SCRIPT_QC, "m", "f", {})
    entry = reg.get(ep_id)
    assert entry["stage"] == Stage.FAILED.value
    assert entry["failed_stage"] == Stage.SCRIPT_QC.value
    assert "ResearchError" in entry["error"]
    assert entry["attempts"] == 1  # bounded: the budget is what caps retries


# --- topic rotation ---------------------------------------------------------


def test_rotation_no_duplicates_and_exhaustion():
    pool = _pool(_topic(tid="t1"), _topic(tid="t2"))
    record: dict = {}
    assert claim_topic(pool, record, "e1")["id"] == "t1"
    assert claim_topic(pool, record, "e2")["id"] == "t2"
    with pytest.raises(ResearchError, match="exhausted"):
        claim_topic(pool, record, "e3")
    # retries keep episode ownership
    assert claim_topic(pool, record, "e1")["id"] == "t1"
    assert claim_topic(pool, record, "e2")["id"] == "t2"


def test_blocked_topic_is_never_reissued():
    pool = _pool(_topic(tid="t1"), _topic(tid="t2"))
    record = {"topics": {"t1": {"status": "blocked", "episode_id": "e1"}}}
    assert claim_topic(pool, record, "e2")["id"] == "t2"


# --- independence rules -----------------------------------------------------


def test_independence_requires_publisher_and_domain():
    assert independent({"publisher": "Org A", "url": "https://a.example/x"},
                       {"publisher": "Org B", "url": "https://b.example/y"})
    assert not independent({"publisher": "Org A", "url": "https://a.example/x"},
                           {"publisher": "Org A", "url": "https://b.example/y"})
    assert not independent({"publisher": "Org A", "url": "https://www.a.example/x"},
                           {"publisher": "Org B", "url": "https://news.a.example/y"})
    assert registrable_domain("https://www.history.com/topics/x") == "history.com"


def test_same_publisher_source_is_not_evidence():
    same_publisher = {**DOC_B, "publisher": "Org A", "text": SRC_B}
    docs = [{**DOC_A, "text": SRC_A}, same_publisher]
    assert supporting_evidence(CLAIM, docs, WIKI) == []
    fresh = [{**DOC_A, "text": SRC_A}, {**DOC_B, "text": SRC_B}]
    assert len(supporting_evidence(CLAIM, fresh, WIKI)) == 2


def test_wikipedia_derivative_source_is_dropped():
    derivative = {**DOC_B, "text": WIKI}  # copied from the discovery article
    docs = [{**DOC_A, "text": SRC_A}, derivative]
    assert supporting_evidence(CLAIM, docs, WIKI) == []


def test_syndicated_duplicates_are_deduped():
    syndicated = {**DOC_B, "text": SRC_A}  # same story, other domain
    assert supporting_evidence(CLAIM, [{**DOC_A, "text": SRC_A}, syndicated], None) == []
    fresh = [{**DOC_A, "text": SRC_A}, {**DOC_B, "text": SRC_B}]
    assert len(supporting_evidence(CLAIM, fresh, None)) == 2


# --- excerpt rules ----------------------------------------------------------


def test_excerpt_is_capped_substring_of_source():
    source = ("The Olympic Games were held every four years at Olympia in Greece, "
              "and athletes travelled from distant city-states to compete in "
              "running, wrestling and chariot races before huge crowds of "
              "spectators who had made the long journey along dusty roads just "
              "to witness the contests.")
    excerpt = best_excerpt(CLAIM, source)
    assert excerpt is not None
    assert len(excerpt) <= EXCERPT_MAX
    assert excerpt in source  # mechanical: never paraphrased


def test_excerpt_requires_supporting_overlap():
    assert best_excerpt(CLAIM, SRC_C) is None
    assert best_excerpt(CLAIM, SRC_A) is not None


# --- claim validation + config gating --------------------------------------


def test_validate_claims_closed_class_and_non_empty():
    assert validate_claims("nope")
    assert validate_claims({"claims": []})
    assert validate_claims({"claims": [{"claim": "x", "class": "vibe"}]})
    assert validate_claims({"claims": [{"claim": "", "class": "fact"}]})
    assert validate_claims(
        {"claims": [{"claim": "Rome built the Colosseum.", "class": "fact"}]}) == []


def test_disabled_research_is_a_noop(tmp_path):
    cfg = _cfg(tmp_path, enabled=False)

    def boom(*a, **k):
        raise AssertionError("disabled research must not run")
    assert run_research(cfg, "s01e002", generate=boom, fetch=boom) is None


def test_research_is_profile_gated_in_configs():
    stickman = json.loads(Path("config/config.stickman.json").read_text(encoding="utf-8"))
    example = json.loads(Path("config/config.example.json").read_text(encoding="utf-8"))
    assert stickman["research"]["enabled"] is True
    assert "research" not in example  # Fernwood: no research config at all


def test_validate_config_requires_pool_when_research_enabled():
    data = json.loads(Path("config/config.stickman.json").read_text(encoding="utf-8"))
    assert validate_config(Config(data=data, path=Path("config/config.stickman.json"))) == []
    data["research"]["pool_path"] = "topics/does-not-exist.json"
    problems = validate_config(Config(data=data, path=Path("config/config.stickman.json")))
    assert any("pool_path" in p for p in problems)


# --- claim coverage in script QC (additive gate) ----------------------------


def _qc_setup(tmp_path, claim: str):
    from app.state import load_registry
    from qc_fixtures import make_valid_package, qc_cfg

    state = tmp_path / "state"
    cfg = qc_cfg(state)
    reg = load_registry(state)
    pkg = make_valid_package()
    ep_id = "s01e001"
    ep_dir = state / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    (ep_dir / "research.json").write_text(
        json.dumps({"claims": [{"claim": claim, "class": "fact"}]}), encoding="utf-8")
    return pkg, cfg, reg, ep_id


def test_claim_coverage_fails_when_script_omits_claim(tmp_path):
    pkg, cfg, reg, ep_id = _qc_setup(
        tmp_path, "Roman gladiators fought inside the Colosseum every year")
    errors, _ = collect_script_errors(pkg, cfg, reg, ep_id)
    assert any("not covered by script" in e for e in errors)


def test_claim_coverage_passes_when_script_states_claim(tmp_path):
    pkg, cfg, reg, ep_id = _qc_setup(
        tmp_path, "The friends play together kindly every day")
    errors, _ = collect_script_errors(pkg, cfg, reg, ep_id)
    assert not [e for e in errors if "not covered" in e]


def test_no_research_json_means_no_coverage_check(tmp_path):
    pkg, cfg, reg, ep_id = _qc_setup(
        tmp_path, "Roman gladiators fought inside the Colosseum every year")
    (tmp_path / "state" / "episodes" / ep_id / "research.json").unlink()
    errors, _ = collect_script_errors(pkg, cfg, reg, ep_id)
    assert not [e for e in errors if "not covered" in e]
