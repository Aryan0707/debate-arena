"""Tests for the provider factory / auto-detection."""

import pytest

from debate_arena.providers import StubProvider, detect_provider, get_provider, list_providers


def test_detect_stub_when_no_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DEBATE_PROVIDER", raising=False)
    assert detect_provider() == "stub"


def test_explicit_name_overrides(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert detect_provider("openai") == "openai"
    assert detect_provider("stub") == "stub"


def test_env_var_overrides_detection(monkeypatch):
    monkeypatch.setenv("DEBATE_PROVIDER", "stub")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert detect_provider() == "stub"


def test_get_provider_returns_stub():
    p = get_provider("stub")
    assert isinstance(p, StubProvider)


def test_get_provider_unknown_raises():
    with pytest.raises(ValueError, match="unknown provider"):
        get_provider("not-a-real-provider")


def test_list_providers():
    providers = list_providers()
    assert "anthropic" in providers
    assert "openai" in providers
    assert "openrouter" in providers
    assert "stub" in providers


def test_anthropic_provider_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        from debate_arena.providers import get_provider
        get_provider("anthropic")


def test_openai_provider_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        from debate_arena.providers import get_provider
        get_provider("openai")


def test_openrouter_provider_requires_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(Exception, match="OPENROUTER_API_KEY"):
        from debate_arena.providers import get_provider
        get_provider("openrouter")
