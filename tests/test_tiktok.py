"""TikTok integration tests: captions, oauth rotation, draft upload, stage wiring.

No network: token/HTTP seams are monkeypatched; publish_shorts runs against
the same fakes as test_youtube.py (TikTok availability is toggled explicitly).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.state import load_registry
from app.tiktok import captions as caps
from app.tiktok import oauth as tt_oauth
from app.tiktok import publish as tt_publish
from app.tiktok.oauth import TikTokCredentialsError
from app.tiktok.publish import TikTokError
from app.youtube import publish
from qc_fixtures import qc_cfg


# --- captions ---------------------------------------------------------------


def test_caption_title_caps_and_brand():
    title = caps.build_title({"title": "Quiet Kindness Lights the Meadow"}, "s01e002")
    assert "Fernwood Friends" in title
    assert len(title) <= caps.TITLE_MAX


def test_caption_title_long_hook_truncated():
    title = caps.build_title({"title": "x" * 200}, "s01e009")
    assert len(title) <= caps.TITLE_MAX


def test_caption_description_parent_directed():
    doc = {"title": "Quiet Kindness", "kind": "wonder", "characters": ["juni", "bramble"]}
    desc = caps.build_description(doc, "s01e002")
    assert desc.startswith("Quiet Kindness.")
    assert "Grown-ups: follow" in desc
    assert "#bedtimestories" in desc and "#fernwoodfriends" in desc
    assert "s01e002" in desc
    assert "subscribe" not in desc.lower()
    assert len(desc) <= caps.DESC_MAX


def test_caption_description_missing_fields_safe():
    desc = caps.build_description({}, "s01e003")
    assert "fernwood friends" in desc.lower()
    assert "#forkids" in desc


# --- oauth ------------------------------------------------------------------


def test_available_requires_client_key(monkeypatch):
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_SECRET", raising=False)
    assert tt_oauth.available() is False
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    assert tt_oauth.available() is True


def test_available_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "REPLACE_ME")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    assert tt_oauth.available() is False


def test_refresh_rotates_and_persists_locally(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("TIKTOK_REFRESH_TOKEN", "rft-old")
    seen = {}

    def fake_post(url, fields, *, timeout=30):
        seen.update(fields)
        return {"access_token": "act-new", "refresh_token": "rft-new", "open_id": "oid"}

    monkeypatch.setattr(tt_oauth, "_post_form", fake_post)
    bundle = tt_oauth.refresh_access(tmp_path)
    assert bundle["access_token"] == "act-new"
    assert seen["grant_type"] == "refresh_token" and seen["refresh_token"] == "rft-old"
    on_disk = json.loads((tmp_path / "secrets" / "tiktok_tokens.json").read_text(encoding="utf-8"))
    assert on_disk["refresh_token"] == "rft-new"


def test_local_rotation_file_wins_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_REFRESH_TOKEN", "rft-env")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "tiktok_tokens.json").write_text(
        json.dumps({"access_token": "act-disk", "refresh_token": "rft-disk"}), encoding="utf-8")
    bundle = tt_oauth._load_bundle(tmp_path)
    assert bundle["refresh_token"] == "rft-disk"
    assert bundle["access_token"] == "act-disk"


def test_refresh_invalid_grant_raises_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    monkeypatch.setenv("TIKTOK_REFRESH_TOKEN", "rft")

    def boom(url, fields, *, timeout=30):
        raise TikTokCredentialsError("tiktok token error invalid_grant: revoked")

    monkeypatch.setattr(tt_oauth, "_post_form", boom)
    with pytest.raises(TikTokCredentialsError, match="invalid_grant"):
        tt_oauth.refresh_access(tmp_path)


def test_missing_refresh_token_mentions_auth_command(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    monkeypatch.delenv("TIKTOK_REFRESH_TOKEN", raising=False)
    with pytest.raises(TikTokCredentialsError, match="tiktok-auth"):
        tt_oauth.refresh_access(tmp_path)


def test_pkce_pair_rfc7636_shapes():
    verifier, challenge = tt_oauth._pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert len(challenge) == 43 and "=" not in challenge
    assert all(c.isalnum() or c in "-_" for c in verifier + challenge)


def test_exchange_code_sends_code_verifier(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    seen = {}

    def fake_post(url, fields, *, timeout=30):
        seen.update(fields)
        return {"access_token": "act", "refresh_token": "rft", "open_id": "oid"}

    monkeypatch.setattr(tt_oauth, "_post_form", fake_post)
    tt_oauth.exchange_code("thecode", tmp_path, code_verifier="v" * 43)
    assert seen["code_verifier"] == "v" * 43
    assert seen["grant_type"] == "authorization_code"


# --- publish ----------------------------------------------------------------


def test_upload_draft_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(tt_publish, "ensure_access_token", lambda state_dir=None: "act")
    calls = {}

    def fake_http(url, payload, token, *, timeout=60):
        calls["url"], calls["payload"], calls["token"] = url, payload, token
        return {"data": {"publish_id": "pid123", "upload_url": "https://up.example/x"}}

    def fake_transfer(url, path, *, timeout=600):
        calls["transfer"] = (url, path.name)

    monkeypatch.setattr(tt_publish, "_http_json", fake_http)
    monkeypatch.setattr(tt_publish, "_transfer_file", fake_transfer)
    video = tmp_path / "short_1.mp4"
    video.write_bytes(b"\x00" * 1024)

    pid = tt_publish.upload_draft(video, "Hook | Fernwood Friends", "desc", state_dir=tmp_path)

    assert pid == "pid123"
    assert calls["token"] == "act"
    assert calls["payload"]["source_info"]["source"] == "FILE_UPLOAD"
    assert calls["payload"]["source_info"]["video_size"] == 1024
    assert calls["payload"]["is_aigc"] is True
    assert calls["payload"]["post_info"]["title"].startswith("Hook")
    assert calls["transfer"] == ("https://up.example/x", "short_1.mp4")


def test_upload_draft_missing_video_raises(tmp_path):
    with pytest.raises(TikTokError, match="video missing"):
        tt_publish.upload_draft(tmp_path / "nope.mp4", "t", "d", state_dir=tmp_path)


def test_upload_draft_init_error_surfaces_code(tmp_path, monkeypatch):
    monkeypatch.setattr(tt_publish, "ensure_access_token", lambda state_dir=None: "act")
    video = tmp_path / "s.mp4"
    video.write_bytes(b"\x00" * 8)

    def fake_http(url, payload, token, *, timeout=60):
        raise TikTokError("init HTTP 403: spam_risk_too_many_pending_share")

    monkeypatch.setattr(tt_publish, "_http_json", fake_http)
    with pytest.raises(TikTokError, match="spam_risk"):
        tt_publish.upload_draft(video, "t", "d", state_dir=tmp_path)


# --- publish_shorts wiring --------------------------------------------------


def _shorts_setup(tmp_path):
    state = tmp_path / "state"
    reg = load_registry(state)
    ep_id = reg.episode_id_for_slot("slot")
    base = state / "episodes" / ep_id
    (base / "render").mkdir(parents=True, exist_ok=True)
    (base / "shorts").mkdir(parents=True, exist_ok=True)
    (base / "package.json").write_text(json.dumps({
        "title": "T", "metadata": {"title": "T | Fernwood Friends S1E01",
                                   "description": "d", "tags": ["kids stories"]},
    }), encoding="utf-8")
    shorts = {}
    for i in (1, 2):
        sid = f"short_{i}"
        doc = base / "shorts" / f"short_{i}.json"
        doc.write_text(json.dumps({"short_id": sid, "title": f"Hook {i}", "kind": "funny",
                                   "characters": ["juni"]}), encoding="utf-8")
        video = base / "render" / f"short_{i}.mp4"
        video.write_bytes(b"\x00" * 4096)
        shorts[sid] = {"status": "rendered", "file": str(doc), "video_path": str(video),
                       "title": f"Hook {i}", "kind": "funny"}
    entry = reg.get(ep_id)
    entry["shorts"] = shorts
    reg.save()
    return qc_cfg(state), reg, ep_id


class _FakeSvc:
    def __init__(self):
        self._videos = self
        self._n = 0

    def videos(self):
        return self

    def list(self, **kw):
        return self

    def execute(self):
        return {"items": [{"status": {"uploadStatus": "processed"}}]}


def _wire_youtube(monkeypatch, notifies):
    monkeypatch.setattr(publish, "build_service", lambda: _FakeSvc())
    counter = {"n": 0}

    def fake_upload(service, path, body, *, label):
        counter["n"] += 1
        return f"vidS{counter['n']}"

    monkeypatch.setattr(publish, "_upload", fake_upload)
    monkeypatch.setattr(publish, "_notify", lambda *a, **kw: notifies.append((a[0], kw)))
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    monkeypatch.setattr(tt_oauth, "available", lambda: True)


def test_shorts_tiktok_drafts_recorded_and_notified(tmp_path, monkeypatch):
    cfg, reg, ep_id = _shorts_setup(tmp_path)
    notifies = []
    _wire_youtube(monkeypatch, notifies)
    drafts = []

    def fake_upload_draft(video_path, title, description, *, state_dir=None):
        drafts.append((Path(video_path).name, title))
        return f"pid{len(drafts)}"

    monkeypatch.setattr("app.tiktok.publish.upload_draft", fake_upload_draft)
    publish.publish_shorts(cfg, reg, ep_id, {})

    shorts = reg.get(ep_id)["shorts"]
    assert shorts["short_1"]["tiktok_publish_id"] == "pid1"
    assert shorts["short_2"]["tiktok_publish_id"] == "pid2"
    assert shorts["short_1"]["tiktok_uploaded_at"]
    assert len(drafts) == 2 and drafts[0][0] == "short_1.mp4"
    tt_msgs = [(m, kw) for m, kw in notifies if "TikTok draft ready" in m]
    assert len(tt_msgs) == 2 and "pid1" in tt_msgs[0][0]
    btn = tt_msgs[0][1]["buttons"][0][0]
    assert btn["text"] == "📮 Post on TikTok" and btn["url"].startswith("https://")


def test_shorts_tiktok_failure_isolated(tmp_path, monkeypatch):
    cfg, reg, ep_id = _shorts_setup(tmp_path)
    notifies = []
    _wire_youtube(monkeypatch, notifies)

    def boom(video_path, title, description, *, state_dir=None):
        raise TikTokError("init HTTP 403: spam_risk_too_many_pending_share")

    monkeypatch.setattr("app.tiktok.publish.upload_draft", boom)
    publish.publish_shorts(cfg, reg, ep_id, {})  # must not raise

    shorts = reg.get(ep_id)["shorts"]
    assert all(shorts[s]["status"] == "uploaded" for s in shorts)  # YouTube unaffected
    assert "spam_risk" in shorts["short_1"]["tiktok_error"]
    assert any("TikTok draft FAILED" in m for m, _kw in notifies)


def test_shorts_tiktok_idempotent_on_rerun(tmp_path, monkeypatch):
    cfg, reg, ep_id = _shorts_setup(tmp_path)
    notifies = []
    _wire_youtube(monkeypatch, notifies)
    calls = []

    def fake_upload_draft(video_path, title, description, *, state_dir=None):
        calls.append(Path(video_path).name)
        return f"pid{len(calls)}"

    monkeypatch.setattr("app.tiktok.publish.upload_draft", fake_upload_draft)
    publish.publish_shorts(cfg, reg, ep_id, {})
    publish.publish_shorts(cfg, reg, ep_id, {})  # nothing pending now
    assert len(calls) == 2  # one per short — no duplicates on rerun


def test_shorts_tiktok_retries_after_earlier_failure(tmp_path, monkeypatch):
    cfg, reg, ep_id = _shorts_setup(tmp_path)
    notifies = []
    _wire_youtube(monkeypatch, notifies)

    def boom(video_path, title, description, *, state_dir=None):
        raise TikTokError("transfer failed")

    monkeypatch.setattr("app.tiktok.publish.upload_draft", boom)
    publish.publish_shorts(cfg, reg, ep_id, {})
    shorts = reg.get(ep_id)["shorts"]
    assert shorts["short_1"].get("tiktok_error")

    calls = []

    def fake_upload_draft(video_path, title, description, *, state_dir=None):
        calls.append(Path(video_path).name)
        return "pidR"

    monkeypatch.setattr("app.tiktok.publish.upload_draft", fake_upload_draft)
    publish.publish_shorts(cfg, reg, ep_id, {})  # no pending YouTube — retries TikTok only
    assert len(calls) == 2
    shorts = reg.get(ep_id)["shorts"]
    assert shorts["short_1"]["tiktok_publish_id"] == "pidR"
    assert "tiktok_error" not in shorts["short_1"]


def test_shorts_tiktok_skipped_without_credentials(tmp_path, monkeypatch):
    cfg, reg, ep_id = _shorts_setup(tmp_path)
    notifies = []
    monkeypatch.setattr(publish, "build_service", lambda: _FakeSvc())
    counter = {"n": 0}

    def fake_upload(service, path, body, *, label):
        counter["n"] += 1
        return f"vidS{counter['n']}"

    monkeypatch.setattr(publish, "_upload", fake_upload)
    monkeypatch.setattr(publish, "_notify", notifies.append)
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_SECRET", raising=False)

    def no_calls(*a, **kw):
        raise AssertionError("tiktok must not be called without credentials")

    monkeypatch.setattr("app.tiktok.publish.upload_draft", no_calls)
    publish.publish_shorts(cfg, reg, ep_id, {})
    shorts = reg.get(ep_id)["shorts"]
    assert shorts["short_1"]["status"] == "uploaded"
    assert "tiktok_publish_id" not in shorts["short_1"]


def test_shorts_tiktok_disabled_in_config(tmp_path, monkeypatch):
    cfg, reg, ep_id = _shorts_setup(tmp_path)
    cfg.data["tiktok"] = {"enabled": False}
    notifies = []
    _wire_youtube(monkeypatch, notifies)

    def no_calls(*a, **kw):
        raise AssertionError("tiktok must not run when disabled")

    monkeypatch.setattr("app.tiktok.publish.upload_draft", no_calls)
    publish.publish_shorts(cfg, reg, ep_id, {})
    assert "tiktok_publish_id" not in reg.get(ep_id)["shorts"]["short_1"]
