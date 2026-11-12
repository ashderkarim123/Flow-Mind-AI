"""Which model the platform assistant talks to is chosen by environment variables."""
import pytest

from app.services import llm_service

KEYS = ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY",
        "ASSISTANT_PROVIDER", "ASSISTANT_MODEL"]


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
