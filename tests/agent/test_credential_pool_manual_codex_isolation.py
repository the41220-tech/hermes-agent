"""A ``manual:device_code`` Codex entry is an independent account grant.

Regression for the pool silently rewriting every manually added Codex login with the singleton
``providers.openai-codex.tokens`` pair: the owner saw one account's email on all seven pooled
labels. Only the singleton-seeded ``device_code`` row may adopt the singleton's rotation.
"""
import json


def _store(tmp_path, singleton_access, singleton_refresh):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "auth.json").write_text(json.dumps({
        "version": 1,
        "providers": {"openai-codex": {"tokens": {"access_token": singleton_access, "refresh_token": singleton_refresh}, "last_refresh": "2026-10-10T00:00:00Z"}},
        "credential_pool": {"openai-codex": [
            {"id": "manual-a", "label": "the41220", "auth_type": "oauth", "priority": 0, "source": "manual:device_code", "access_token": "a-access", "refresh_token": "a-refresh"},
            {"id": "seeded", "label": "jangyoon", "auth_type": "oauth", "priority": 1, "source": "device_code", "access_token": "old-access", "refresh_token": "old-refresh"},
        ]},
    }))
    return home


def test_manual_codex_entry_keeps_its_own_grant_when_singleton_rotates(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(_store(tmp_path, "singleton-access", "singleton-refresh")))
    from agent.credential_pool import load_pool

    pool = load_pool("openai-codex")
    by_id = {entry.id: entry for entry in pool._entries}
    manual = pool._sync_entry_from_auth_store(by_id["manual-a"])
    seeded = pool._sync_entry_from_auth_store(by_id["seeded"])

    assert (manual.access_token, manual.refresh_token) == ("a-access", "a-refresh")
    assert (seeded.access_token, seeded.refresh_token) == ("singleton-access", "singleton-refresh")


def test_failed_refresh_of_manual_codex_entry_never_adopts_singleton_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(_store(tmp_path, "singleton-access", "singleton-refresh")))
    from agent.credential_pool import load_pool

    pool = load_pool("openai-codex")
    manual = next(entry for entry in pool._entries if entry.id == "manual-a")
    recovered = pool._recover_failed_refresh(manual, RuntimeError("transient"))

    assert recovered is None
    persisted = {e["id"]: e for e in json.loads((tmp_path / "hermes" / "auth.json").read_text())["credential_pool"]["openai-codex"]}
    assert persisted["manual-a"]["access_token"] == "a-access"
    assert persisted["manual-a"]["refresh_token"] == "a-refresh"
