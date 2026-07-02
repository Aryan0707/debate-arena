# 🥊 Multi-Claude Debate Arena

[![Tests](https://github.com/Aryan0707/debate-arena/actions/workflows/tests.yml/badge.svg)](https://github.com/Aryan0707/debate-arena/actions/workflows/tests.yml)
[![Lint](https://github.com/Aryan0707/debate-arena/actions/workflows/lint.yml/badge.svg)](https://github.com/Aryan0707/debate-arena/actions/workflows/lint.yml)
[![Build](https://github.com/Aryan0707/debate-arena/actions/workflows/build.yml/badge.svg)](https://github.com/Aryan0707/debate-arena/actions/workflows/build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Aryan0707/debate-arena?style=social)](https://github.com/Aryan0707/debate-arena/stargazers)

> Watch AIs argue it out, then get the synthesized answer.

Multi-agent debate system that spawns 3-4 AI agents with different personas (Skeptic, Optimist, Engineer, Devil's Advocate) to argue a question, then synthesizes the best answer. Supports Anthropic Claude, OpenAI, OpenRouter, or any OpenAI-compatible API. Demo mode runs offline with no API.

## ⚡ Quick start

```bash
# Install
pip install -e .

# Run with your API (auto-detects which is set)
export ANTHROPIC_API_KEY=sk-...  # or OPENAI_API_KEY, or OPENROUTER_API_KEY
debate "Should I quit my job to start a company?"

# Or with explicit provider/model
debate --provider openrouter --model anthropic/claude-3.5-sonnet "Best stack for a SaaS MVP?"

# Demo mode (no API needed, uses local stub agents)
debate --demo "What's the meaning of life?"
```

## 🎭 Personas (11 built-in)

- **Skeptic** — pokes holes, demands evidence, plays devil's advocate
- **Optimist** — sees upside, advocates bold action
- **Engineer** — focuses on feasibility, cost, maintenance, scaling
- **Strategist** — long-term, second-order effects, game theory
- **Moderator** — synthesizes the debate into a final answer
- **Hacker** — looks for exploits, leverage, asymmetric plays, clever workarounds
- **Regulator** — compliance, legal risk, public policy, societal effects
- **Philosopher** — long-term ethics, deeper meaning, reframes the question
- **Trader** — financial risk, market timing, expected value, position sizing
- **Customer** — voice of the actual end user, grounds debates in real humans
- **First Principles** — strips away assumptions, rebuilds from ground truth

Mix and match — try `--personas hacker,regulator,engineer,customer` for a really spicy take on a product decision, or `--personas philosopher,trader,first-principles` for a strategic question.

## 🔁 Debate flow

```
Phase 1: OPENING     — each persona states initial position
Phase 2: CROSSFIRE   — each persona sees others, rebuts/revises
Phase 3: SYNTHESIS   — moderator picks the strongest points
```

## 🛠️ CLI

```
debate "your question"                           # basic
debate -p openrouter -m claude-3.5-sonnet "..."  # pick provider/model
debate --rounds 2 "..."                          # multiple crossfire rounds
debate --personas skeptic,optimist "..."         # pick subset of personas
debate --no-synthesis "..."                      # skip synthesis, raw debate
debate --export debate.md "..."                  # save full transcript
debate --demo "..."                              # no API, local stubs
```

## 🦙 Local models with Ollama (free, private, offline)

If you have [Ollama](https://ollama.ai) installed and running locally, the
debate arena auto-detects it — no API key required:

```bash
# Install Ollama (Mac)
brew install ollama

# Pull a model
ollama pull llama3.2

# Use it (auto-detected, or explicit)
debate --provider ollama --model llama3.2 "Your question"
debate -p ollama -m qwen2.5:7b --rounds 2 "Your question"

# Set defaults via env vars
export OLLAMA_MODEL=qwen2.5:7b
export OLLAMA_HOST=http://my-ollama-server:11434   # if remote
```

The first call to a model can take 10-30s while Ollama loads it into RAM.
Subsequent calls are fast. The provider's timeout is bumped to 5 minutes
to handle cold loads on large models.

Recommended models for debate (good at following persona instructions):
- `llama3.2` (3B) — fast, surprisingly good, runs on any Mac
- `qwen2.5:7b` — better reasoning, needs ~6GB RAM
- `mistral` (7B) — strong all-rounder
- `qwen2.5:14b` — best quality under 16GB RAM


## 🌐 Web UI

A Gradio UI ships with the project:

```bash
pip install -e ".[web]"
python examples/web_ui.py                # opens http://127.0.0.1:7860
python examples/web_ui.py --share        # creates a public gradio.live URL
python examples/web_ui.py --port 8080    # change port
```

The UI streams the debate panel-by-panel, shows the final synthesis, and lets you download the full transcript as Markdown.

## 📦 Python API

```python
from debate_arena import DebateArena, DebateConfig
from debate_arena.providers import AnthropicProvider

config = DebateConfig(
    question="Should AI be regulated?",
    personas=["skeptic", "optimist", "engineer"],
    rounds=2,
)
arena = DebateArena(provider=AnthropicProvider(model="claude-3-5-sonnet-20241022"))
result = arena.run(config)
print(result.synthesis)
for turn in result.transcript:
    print(f"\n=== {turn.persona} (round {turn.round}) ===")
    print(turn.content)
```

## 🧩 Add your own persona

```yaml
# personas/hacker.yaml
id: hacker
name: Hacker
system_prompt: |
  You are a Hacker persona. You look for exploits, shortcuts, and unconventional
  solutions. You think in terms of leverage, asymmetry, and "what's the minimum
  viable hack". You distrust best practices and love clever workarounds.
temperature: 0.9
```

## 🧪 Development

```bash
pip install -e ".[dev]"
pytest -v
```

## 🔄 Continuous integration

Every push and PR runs through [GitHub Actions](.github/workflows/):

- **Tests** — 73 tests on Python 3.10, 3.11, 3.12, 3.13
- **Lint** — ruff check + format check
- **Build** — sdist + wheel, verified by installing and running the CLI
- **Dependabot** — weekly PRs for dependency updates

Coverage is uploaded to Codecov on Python 3.12 pushes to main.

## 📄 License

MIT
