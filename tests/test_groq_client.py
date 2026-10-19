"""Groq failover + JSON extraction tests (§25, §42)."""

import json

import pytest

from app.groq_client import GroqClient, GroqExhausted, GroqKeyPool, extract_json


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    text = 'Sure! ```json\n{"title": "X"}\n``` done'
    assert extract_json(text) == {"title": "X"}


def test_extract_json_with_prose_around():
    text = 'Here you go: {"k": [1,2]} hope that helps'
    assert extract_json(text) == {"k": [1, 2]}


def test_extract_json_array():
    assert extract_json("[1, 2, 3]") == [1, 2, 3]


def test_extract_json_garbage_raises():
    with pytest.raises(ValueError):
        extract_json("no json here at all")


def test_key_pool_rotation_and_auth_exhaustion():
    pool = GroqKeyPool(["k1", "k2"])
    assert pool.current() == (0, "k1")
    pool.mark_auth_failed()
    pool.rotate()
    assert pool.current() == (1, "k2")
    pool.mark_auth_failed()
    with pytest.raises(GroqExhausted):
        pool.rotate()


def test_key_pool_single_slot():
    pool = GroqKeyPool(["only"])
    pool.rotate()  # wraps back to 0 (not disabled yet)
    assert pool.current() == (0, "only")
    pool.mark_auth_failed()
    with pytest.raises(GroqExhausted):
        pool.rotate()


class _FakeHTTP:
    """Scripted responses: list of (status, body_dict_or_str[, retry_after])."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.seen_models: list[str] = []

    def __call__(self, payload, key, timeout):
        self.calls += 1
        self.seen_models.append(str(payload.get("model")))
        row = self.script.pop(0)
        status, body = row[0], row[1]
        retry_after = row[2] if len(row) > 2 else None
        if isinstance(body, dict):
            body = json.dumps(body)
        return status, body, retry_after


def _ok_body(content="hello"):
    # Real generations are thousands of chars; the client treats <300-char
    # replies as TPM-degraded, so fixtures must look real-sized.
    return {"choices": [{"message": {"content": content + " " + "x" * 400}}]}


def test_client_success_first_try():
    from app import groq_client

    orig = groq_client._post_chat
    groq_client._post_chat = _FakeHTTP([(200, _ok_body("hi"))])
    try:
        client = GroqClient(["k1"], model="m", sleep=lambda s: None, max_attempts=3)
        out = client.chat([{"role": "user", "content": "x"}])
        assert out.startswith("hi")
    finally:
        groq_client._post_chat = orig


def test_client_429_waits_full_window_then_rotates_slot():
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(429, ""), (200, _ok_body("ok"))])
    groq_client._post_chat = fake
    try:
        client = GroqClient(["k1", "k2"], model="m", sleep=lambda s: None, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("ok")
        assert fake.calls == 2
        # Full minute-window wait, THEN rotate: same-org keys share the TPM
        # pool (no-op), different-org keys each get their own window.
        assert client.pool.current()[0] == 1
    finally:
        groq_client._post_chat = orig


def test_client_429_rotates_to_fallback_model():
    """After the minute-window wait the NEXT attempt uses the fallback model
    (its own free-tier TPM pool) — the lever that helps when the whole org is
    blocked on the primary model."""
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(429, ""), (200, _ok_body("ok"))])
    groq_client._post_chat = fake
    try:
        client = GroqClient(["k1"], model="big", models=["big", "small"],
                            sleep=lambda s: None, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("ok")
        assert fake.seen_models == ["big", "small"]
        # a new call starts back on the primary model
        groq_client._post_chat = _FakeHTTP([(200, _ok_body("again"))])
        client.chat([{"role": "user", "content": "x"}])
        assert groq_client._post_chat.seen_models == ["big"]
    finally:
        groq_client._post_chat = orig


def test_client_auth_failure_exhausts_all_slots():
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(401, ""), (401, "")])
    groq_client._post_chat = fake
    try:
        client = GroqClient(["k1", "k2"], model="m", sleep=lambda s: None, max_attempts=6)
        with pytest.raises(GroqExhausted):
            client.chat([{"role": "user", "content": "x"}])
        assert fake.calls == 2  # one auth attempt per slot, then stop
    finally:
        groq_client._post_chat = orig


def test_client_5xx_backoff_bounded_attempts():
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(500, "")] * 3)
    groq_client._post_chat = fake
    try:
        client = GroqClient(["k1"], model="m", sleep=lambda s: None, max_attempts=3)
        with pytest.raises(GroqExhausted):
            client.chat([{"role": "user", "content": "x"}])
        assert fake.calls == 3  # never retries forever
    finally:
        groq_client._post_chat = orig


def test_client_429_honors_larger_retry_after():
    """A Retry-After LARGER than the TPM minute window is honoured (capped at 120s)."""
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(429, "", 90), (200, _ok_body("ok"))])
    groq_client._post_chat = fake
    slept: list = []
    try:
        client = GroqClient(["k1"], model="m", sleep=slept.append, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("ok")
        assert slept == [90.0]  # server asked for 90s (> 70s window) — honoured
        assert client.pool.current()[0] == 0  # org-wide limits: same slot
    finally:
        groq_client._post_chat = orig


def test_client_429_without_retry_after_waits_fixed_window():
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(429, ""), (200, _ok_body("ok"))])
    groq_client._post_chat = fake
    slept: list = []
    try:
        client = GroqClient(["k1"], model="m", sleep=slept.append, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("ok")
        assert slept == [70.0]
    finally:
        groq_client._post_chat = orig


def test_client_429_ignores_tiny_retry_after():
    """A tiny Retry-After (RPM resets before TPM) is IGNORED — the full minute
    window is always waited so consecutive TPM hits cannot burn the attempt
    budget a second apart. This was the root cause of a script call starving
    against a still-blocked TPM window."""
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(429, "", 1), (429, "", 1), (200, _ok_body("ok"))])
    groq_client._post_chat = fake
    slept: list = []
    try:
        client = GroqClient(["k1"], model="m", sleep=slept.append, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("ok")
        assert slept == [70.0, 70.0]  # tiny Retry-After ignored; wait the window
        assert client.pool.current()[0] == 0
    finally:
        groq_client._post_chat = orig


def _validate_fail(failed_generation: str):
    return {"error": {"message": "Failed to generate JSON. Please adjust your prompt.",
                      "type": "invalid_request_error", "code": "json_validate_failed",
                      "failed_generation": failed_generation}}


def test_client_tiny_content_waits_full_window():
    """A sub-300-char reply is Groq's degradation signature (serves instant
    junk while the TPM window is hot) — wait the FULL window, don't burn the
    attempt on it."""
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(200, {"choices": [{"message": {"content": "{}"}}]}),
                      (200, _ok_body("good"))])
    groq_client._post_chat = fake
    slept: list = []
    try:
        client = GroqClient(["k1"], model="m", sleep=slept.append, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("good")
        assert slept == [70.0]
        assert fake.calls == 2
    finally:
        groq_client._post_chat = orig


def test_client_short_prose_failed_generation_waits_full_window():
    """400 json_validate_failed with a SHORT failed_generation (prose
    apology like "I'm sorry…") is the same degradation → full window wait."""
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(400, _validate_fail("I'm sorry, I can't do that.")),
                      (200, _ok_body("good"))])
    groq_client._post_chat = fake
    slept: list = []
    try:
        client = GroqClient(["k1"], model="m", sleep=slept.append, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("good")
        assert slept == [70.0]
        assert fake.calls == 2
    finally:
        groq_client._post_chat = orig


def test_client_long_failed_generation_uses_normal_backoff():
    """A LONG failed_generation is a genuine schema miss — normal short
    backoff, the engine's repair loop handles content quality."""
    from app import groq_client

    orig = groq_client._post_chat
    fake = _FakeHTTP([(400, _validate_fail('{"wrong": "' + "z" * 1500 + '"}')),
                      (200, _ok_body("good"))])
    groq_client._post_chat = fake
    slept: list = []
    try:
        client = GroqClient(["k1"], model="m", sleep=slept.append, max_attempts=4)
        assert client.chat([{"role": "user", "content": "x"}]).startswith("good")
        assert slept and slept[0] < 10  # exponential backoff, not a 70s window
    finally:
        groq_client._post_chat = orig
