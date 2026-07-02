# 🥊 Multi-Claude Debate Arena

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

## 🎭 Built-in personas

- **Skeptic** — pokes holes, demands evidence, plays devil's advocate
- **Optimist** — sees upside, advocates bold action
- **Engineer** — focuses on feasibility, cost, maintenance, scaling
- **Strategist** — long-term, second-order effects, game theory
- *(add your own in `personas/*.yaml`)*

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

## 📄 License

MIT
