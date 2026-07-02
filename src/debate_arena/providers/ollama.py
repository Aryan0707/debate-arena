"""Ollama provider — talks to a local Ollama server via its OpenAI-compatible API.

Ollama (https://ollama.ai) runs LLMs locally on your machine. It's free, private,
and offline-capable. This provider talks to Ollama's OpenAI-compatible endpoint
at http://127.0.0.1:11434/v1.

Setup:
    1. Install Ollama from https://ollama.ai (Mac: `brew install ollama`)
    2. Pull a model: `ollama pull llama3.2` (or qwen2.5, mistral, etc.)
    3. Make sure the server is running: `ollama serve` (or it auto-starts)
    4. Use it:
         export OLLAMA_HOST=http://127.0.0.1:11434  # optional, this is the default
         debate --provider ollama --model llama3.2 "Your question"

Or set a default model so you don't have to pass --model every time:
    export OLLAMA_MODEL=llama3.2
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from debate_arena.providers.base import (
    Completion,
    Message,
    ProviderError,
    env_or,
)
from debate_arena.providers.openai import OpenAIProvider

OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL = "llama3.2"


@dataclass
class OllamaProvider(OpenAIProvider):
    """Ollama provider. Uses the same wire format as OpenAI Chat Completions.

    Ollama exposes an OpenAI-compatible API at /v1, so we just point our
    OpenAI-compatible client at it. No API key required.

    Notable: unlike OpenAI/Anthropic, Ollama models can take a while to load
    on the first call (especially big models). The timeout is bumped to 5
    minutes by default to handle cold loads.
    """

    name: str = "ollama"
    default_model: str = DEFAULT_MODEL
    base_url: str = OLLAMA_DEFAULT_URL
    timeout: float = 300.0  # 5 min — first call may need to load the model

    def __post_init__(self) -> None:
        # Ollama doesn't need an API key, but the OpenAI client base expects one
        # in the Authorization header. We pass a dummy "ollama" string.
        self.api_key = self.api_key or env_or("ollama", "OLLAMA_API_KEY")
        # Allow OLLAMA_HOST env var to override the base URL
        self.base_url = env_or(self.base_url, "OLLAMA_HOST")
        # OLLAMA_MODEL env var sets the default model
        env_default = env_or("", "OLLAMA_MODEL")
        if env_default and self.default_model == DEFAULT_MODEL:
            self.default_model = env_default

    def _check_server(self) -> None:
        """Verify the Ollama server is reachable before making API calls.

        Raises a clear ProviderError if not, so the user sees something useful
        instead of an httpx connection error.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                # Hit the root endpoint — returns "Ollama is running" if up
                resp = client.get(self.base_url.rstrip("/v1") + "/api/tags")
                if resp.status_code >= 400:
                    raise ProviderError(
                        f"Ollama server at {self.base_url} returned {resp.status_code}. "
                        f"Make sure Ollama is running (`ollama serve` or check the menu bar app)."
                    )
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Can't reach Ollama at {self.base_url}. "
                f"Start it with `ollama serve` or open the Ollama app. "
                f"Then pull a model: `ollama pull llama3.2`"
            ) from e
        except httpx.HTTPError as e:
            raise ProviderError(f"Ollama health check failed: {e}") from e

    def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Completion:
        # Health check on first call so we fail fast with a clear message.
        self._check_server()
        return super().complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
