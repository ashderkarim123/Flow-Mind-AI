"""Which model the platform assistant talks to is chosen by environment variables."""
import pytest

from app.services import llm_service

KEYS = ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY",
        "ASSISTANT_PROVIDER", "ASSISTANT_MODEL",
        "ASSISTANT_FALLBACK_BASE_URL", "ASSISTANT_FALLBACK_API_KEY", "ASSISTANT_FALLBACK_MODEL"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)


def test_openrouter_explicit(monkeypatch):
    monkeypatch.setenv("ASSISTANT_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    ep = llm_service.endpoint()
    assert (ep.provider, ep.base_url, ep.api_key) == ("openrouter", "https://openrouter.ai/api/v1", "sk-or-x")
    monkeypatch.setenv("ASSISTANT_MODEL", "anthropic/claude-sonnet-4.5")
    assert llm_service.endpoint().model == "anthropic/claude-sonnet-4.5"


def test_openrouter_without_key_says_what_to_set(monkeypatch):
    monkeypatch.setenv("ASSISTANT_PROVIDER", "openrouter")
    with pytest.raises(llm_service.LLMUnavailable, match="OPENROUTER_API_KEY"):
        llm_service.endpoint()


def test_auto_picks_the_provider_that_has_a_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    assert llm_service.endpoint().provider == "openrouter"
    monkeypatch.delenv("OPENROUTER_API_KEY")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert llm_service.endpoint().provider == "anthropic"


def _run_chat(monkeypatch, fail_urls):
    """chat() with the HTTP layer faked: servers whose base_url is in fail_urls are unavailable."""
    import asyncio
    calls = []

    async def fake_once(messages, ep, **options):
        calls.append((ep.provider, ep.base_url, ep.model, ep.api_key))
        if ep.base_url in fail_urls:
            raise llm_service.LLMUnavailable(f"{ep.provider} down.")
        return f"answer from {ep.provider}"

    monkeypatch.setattr(llm_service, "_chat_once", fake_once)
    return calls, lambda: asyncio.run(llm_service.chat([{"role": "user", "content": "hi"}]))


def test_fallback_used_when_primary_is_down(monkeypatch):
    monkeypatch.setenv("ASSISTANT_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("ASSISTANT_FALLBACK_BASE_URL", "https://backup.example/v1/")
    monkeypatch.setenv("ASSISTANT_FALLBACK_API_KEY", "sk-backup")
    calls, run = _run_chat(monkeypatch, {"https://openrouter.ai/api/v1"})
    assert run() == "answer from fallback"
    assert calls[1] == ("fallback", "https://backup.example/v1", "gpt-4.1-mini", "sk-backup")   # vendor prefix dropped


def test_fallback_used_when_primary_has_no_key(monkeypatch):
    monkeypatch.setenv("ASSISTANT_PROVIDER", "openrouter")   # no OPENROUTER_API_KEY
    monkeypatch.setenv("ASSISTANT_FALLBACK_BASE_URL", "https://backup.example/v1")
    monkeypatch.setenv("ASSISTANT_FALLBACK_MODEL", "some-model")
    calls, run = _run_chat(monkeypatch, set())
    assert run() == "answer from fallback" and calls[0][2] == "some-model"


def test_no_fallback_configured_keeps_the_original_error(monkeypatch):
    monkeypatch.setenv("ASSISTANT_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    _, run = _run_chat(monkeypatch, {"https://openrouter.ai/api/v1"})
    with pytest.raises(llm_service.LLMUnavailable, match="openrouter down"):
        run()


def test_both_down_reports_both(monkeypatch):
    monkeypatch.setenv("ASSISTANT_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("ASSISTANT_FALLBACK_BASE_URL", "https://backup.example/v1")
    _, run = _run_chat(monkeypatch, {"https://openrouter.ai/api/v1", "https://backup.example/v1"})
    with pytest.raises(llm_service.LLMUnavailable, match="openrouter down.*fallback down"):
        run()
