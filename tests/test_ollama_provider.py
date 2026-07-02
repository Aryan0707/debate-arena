"""Tests for the Ollama provider.

These tests don't require Ollama to actually be running — they verify
the provider's setup, error handling, and the auto-detection logic
that uses it.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from debate_arena.providers import (
    OllamaProvider,
    detect_provider,
    get_provider,
    list_providers,
)
from debate_arena.providers.base import ProviderError


def test_ollama_in_list_providers():
    assert "ollama" in list_providers()


def test_ollama_provider_construction_no_key_needed():
    """Ollama doesn't need an API key."""
    p = OllamaProvider()
    assert p.name == "ollama"
    assert p.api_key  # gets a dummy "ollama" value, not None
    assert p.default_model == "llama3.2"
    assert p.base_url == "http://127.0.0.1:11434/v1"


def test_ollama_provider_uses_ollama_host_env():
    with patch.dict("os.environ", {"OLLAMA_HOST": "http://myhost:9999"}):
        p = OllamaProvider()
        assert p.base_url == "http://myhost:9999"


def test_ollama_provider_uses_ollama_model_env():
    with patch.dict("os.environ", {"OLLAMA_MODEL": "qwen2.5:7b"}):
        p = OllamaProvider()
        assert p.default_model == "qwen2.5:7b"


def test_ollama_provider_uses_explicit_model_over_env():
    with patch.dict("os.environ", {"OLLAMA_MODEL": "qwen2.5:7b"}):
        p = OllamaProvider(model="custom-model")
        # Per-instance model takes precedence
        assert p.model == "custom-model"


def test_detect_provider_prefers_ollama_when_no_keys_set():
    """If no API keys are set but ollama is running, use ollama."""
    env = {
        k: "" for k in [
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
            "DEBATE_PROVIDER",
        ]
    }
    with patch.dict("os.environ", env, clear=True):
        with patch(
            "debate_arena.providers.factory._ollama_reachable", return_value=True
        ):
            assert detect_provider() == "ollama"


def test_detect_provider_falls_back_to_stub_when_nothing_available():
    env = {
        k: "" for k in [
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
            "DEBATE_PROVIDER",
        ]
    }
    with patch.dict("os.environ", env, clear=True):
        with patch(
            "debate_arena.providers.factory._ollama_reachable", return_value=False
        ):
            assert detect_provider() == "stub"


def test_ollama_unreachable_raises_clear_error():
    """If the server isn't running, we get a clear error, not a generic HTTP error."""
    p = OllamaProvider()
    with patch("httpx.Client.get") as mock_get:
        import httpx
        mock_get.side_effect = httpx.ConnectError("connection refused")
        with pytest.raises(ProviderError, match="ollama serve"):
            p._check_server()


def test_ollama_server_error_raises_clear_error():
    p = OllamaProvider()
    with patch("httpx.Client.get") as mock_get:
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.status_code = 500
        mock_get.return_value = resp
        with pytest.raises(ProviderError, match="500"):
            p._check_server()


def test_get_provider_returns_ollama():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=True):
        p = get_provider("ollama")
        assert isinstance(p, OllamaProvider)
