"""Professional Gradio web UI for the debate arena.

Run with:
    python examples/web_ui.py                    # demo mode (no API key)
    ANTHROPIC_API_KEY=*** python examples/web_ui.py
    python examples/web_ui.py --share            # public gradio.live URL
    python examples/web_ui.py --port 8080        # change port
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure the package is importable when running directly from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import gradio as gr

from debate_arena import DebateArena, DebateConfig
from debate_arena.models import PersonaTurn
from debate_arena.personas import PERSONAS_DIR
from debate_arena.presets import load_presets
from debate_arena.providers import detect_provider, get_provider

PRESETS = load_presets()

AVAILABLE_PERSONAS = sorted(p.stem for p in PERSONAS_DIR.glob("*.yaml"))
DEFAULT_PERSONAS = ["skeptic", "optimist", "engineer"]

# Visual config for persona cards
PERSONA_META = {
    "skeptic": {"emoji": "🔍", "tagline": "Pokes holes, demands evidence", "color": "#ef4444"},
    "optimist": {
        "emoji": "🚀",
        "tagline": "Sees upside, advocates bold action",
        "color": "#f59e0b",
    },
    "engineer": {"emoji": "🔨", "tagline": "Feasibility, cost, scaling", "color": "#3b82f6"},
    "strategist": {
        "emoji": "♟️",
        "tagline": "Long-term, game theory, 2nd order",
        "color": "#8b5cf6",
    },
    "moderator": {"emoji": "⚖️", "tagline": "Synthesizes the final answer", "color": "#10b981"},
    "hacker": {
        "emoji": "💻",
        "tagline": "Leverage, exploits, asymmetric plays",
        "color": "#ec4899",
    },
    "regulator": {"emoji": "📜", "tagline": "Compliance, legal risk, policy", "color": "#6366f1"},
    "philosopher": {"emoji": "🏛️", "tagline": "Ethics, meaning, reframes the Q", "color": "#14b8a6"},
    "trader": {"emoji": "📈", "tagline": "Expected value, position sizing", "color": "#84cc16"},
    "customer": {"emoji": "👤", "tagline": "Voice of the actual end user", "color": "#f97316"},
    "first-principles": {
        "emoji": "🧬",
        "tagline": "Strips assumptions, demands rigor",
        "color": "#06b6d4",
    },
}


def apply_preset(preset_id: str) -> tuple[str, list[str], int, str, str]:
    """Look up a preset and return (question, personas, rounds, status_banner, active_id).

    Returns the new values for the question field, persona checkboxes, rounds slider,
    a status banner confirming the preset was applied, and the preset id to record
    as the active one.
    """
    if not preset_id:
        return gr.update(), gr.update(), gr.update(), "", ""
    from debate_arena.presets import get_preset
    preset = get_preset(preset_id)
    if not preset:
        return gr.update(), gr.update(), gr.update(), "", ""
    banner = (
        f'<div class="status-banner info">⚡ <strong>{preset.emoji} {preset.name}</strong> preset applied. '
        f'Edit anything below before hitting Start.</div>'
    )
    return (
        preset.example_question,
        preset.personas,
        preset.rounds,
        banner,
        preset.id,
    )


def render_persona_chips(selected: list[str]) -> str:
    """Render selected personas as colored HTML chips for display above the run button."""
    if not selected:
        return '<div class="empty-chips">No personas selected</div>'
    chips = []
    for pid in selected:
        meta = PERSONA_META.get(pid, {"emoji": "•", "tagline": "", "color": "#64748b"})
        chips.append(
            f'<span class="persona-chip" style="--chip-color: {meta["color"]}">'
            f'<span class="chip-emoji">{meta["emoji"]}</span>'
            f'<span class="chip-name">{pid.replace("-", " ").title()}</span>'
            f'<span class="chip-tagline">{meta["tagline"]}</span>'
            f"</span>"
        )
    return f'<div class="chips-row">{"".join(chips)}</div>'


def render_preset_chips() -> str:
    """Render the preset buttons as a horizontal row of clickable cards."""
    if not PRESETS:
        return ""
    cards = []
    for preset in PRESETS:
        cards.append(
            f'<button type="button" class="preset-card" data-preset-id="{preset.id}" '
            f'style="--accent: {preset.color}">'
            f'<span class="preset-emoji">{preset.emoji}</span>'
            f'<span class="preset-name">{preset.name}</span>'
            f'<span class="preset-desc">{preset.description}</span>'
            f"</button>"
        )
    return f'<div class="preset-row">{"".join(cards)}</div>'


def persona_choices_with_meta() -> list[tuple[str, str]]:
    """Format persona choices for Gradio's CheckboxGroup: (label, value)."""
    out = []
    for pid in AVAILABLE_PERSONAS:
        meta = PERSONA_META.get(pid, {"emoji": "•", "tagline": ""})
        label = f"{meta['emoji']}  {pid.replace('-', ' ').title()}  —  {meta['tagline']}"
        out.append((label, pid))
    return out


def run_debate(
    question: str,
    personas: list[str],
    rounds: int,
    provider_name: str,
    model: str,
    use_demo: bool,
    progress=gr.Progress(track_tqdm=False),
):
    """Stream the debate as it happens, yielding (status, synthesis, md, chips, share_url) tuples."""
    if not question or not question.strip():
        yield (
            '<div class="status-banner error">⚠️ Please enter a question.</div>',
            "",
            "",
            '<div class="empty-chips">No personas selected</div>',
            "",
        )
        return
    if not personas:
        yield (
            '<div class="status-banner error">⚠️ Please select at least one persona.</div>',
            "",
            "",
            '<div class="empty-chips">No personas selected</div>',
            "",
        )
        return

    if use_demo:
        provider_name = "stub"

    try:
        provider = get_provider(provider_name, model=model or None)
    except Exception as e:
        yield (
            f'<div class="status-banner error">❌ Could not set up provider: {e}</div>',
            "",
            "",
            render_persona_chips(personas),
            "",
        )
        return

    arena = DebateArena(provider=provider, stream=False)

    import json as _json
    config = DebateConfig(
        question=question,
        personas=personas,
        rounds=rounds,
        model=model or None,
        provider=detect_provider(provider_name),
    )
    config_json = _json.dumps({
        "personas": config.personas,
        "rounds": config.rounds,
        "moderator": config.moderator,
        "model": config.model,
        "provider": config.provider,
    })

    transcript_md: list[str] = [f"# 🥊 {question}\n"]
    synthesis_text = ""
    transcript_turns: list[PersonaTurn] = []

    chips_html = render_persona_chips(personas)
    yield (
        '<div class="status-banner info">🥊 <strong>Opening statements...</strong></div>',
        "",
        "\n".join(transcript_md),
        chips_html,
        "",
    )

    try:
        from debate_arena.personas import load_personas
        from debate_arena.providers.base import Message, ProviderError

        personas_objs = load_personas(config.personas)
        total_usage: dict = {}
        total_steps = len(personas_objs) + len(personas_objs) * config.rounds + 1
        step = 0

        # Phase 1: openings
        for persona in personas_objs:
            step += 1
            progress((step, total_steps), f"Opening: {persona.name}")
            yield (
                f'<div class="status-banner info">🥊 <strong>{persona.name}</strong> is delivering opening statement...</div>',
                "",
                "\n".join(transcript_md),
                chips_html,
                "",
            )

            turn = arena._run_turn(
                persona=persona,
                question=config.question,
                prior_turns=[],
                round_num=1,
                phase="opening",
                model=config.model,
            )
            transcript_turns.append(turn)
            meta = PERSONA_META.get(persona.id, {"emoji": "•"})
            transcript_md.append(
                f"\n## {meta['emoji']} {persona.name} — Round 1 · opening\n\n{turn.content}\n"
            )
            for k, v in turn.usage.items():
                total_usage[k] = total_usage.get(k, 0) + v

        # Phase 2: crossfire
        for r in range(1, config.rounds + 1):
            for persona in personas_objs:
                step += 1
                progress((step, total_steps), f"Crossfire {r}: {persona.name}")
                yield (
                    f'<div class="status-banner warn">⚔️  <strong>{persona.name}</strong> is rebutting (round {r})...</div>',
                    "",
                    "\n".join(transcript_md),
                    chips_html,
                    "",
                )

                others = [t for t in transcript_turns if t.persona != persona.id]
                recent = others[-len(personas_objs):] if len(others) >= len(personas_objs) else others
                prior_text = [f"[{t.persona}]\n{t.content}" for t in recent]

                turn = arena._run_turn(
                    persona=persona,
                    question=config.question,
                    prior_turns=prior_text,
                    round_num=r,
                    phase="rebuttal",
                    model=config.model,
                )
                transcript_turns.append(turn)
                meta = PERSONA_META.get(persona.id, {"emoji": "•"})
                transcript_md.append(
                    f"\n## {meta['emoji']} {persona.name} — Round {r} · rebuttal\n\n{turn.content}\n"
                )
                for k, v in turn.usage.items():
                    total_usage[k] = total_usage.get(k, 0) + v

        # Phase 3: synthesis
        step += 1
        progress((step, total_steps), "Moderator synthesizing...")
        yield (
            '<div class="status-banner synth">🏁 <strong>Moderator</strong> is synthesizing the final answer...</div>',
            "",
            "\n".join(transcript_md),
            chips_html,
            "",
        )

        try:
            moderator = load_personas([config.moderator])[0]
        except FileNotFoundError:
            moderator = load_personas(["engineer"])[0]

        full_transcript_text = "\n\n---\n\n".join(
            f"[{t.persona} — round {t.round} · {t.phase}]\n{t.content}" for t in transcript_turns
        )
        try:
            completion = arena.provider.complete(
                [
                    Message(role="system", content=moderator.system_prompt),
                    Message(
                        role="user",
                        content=(
                            f"QUESTION: {config.question}\n\n"
                            f"FULL DEBATE TRANSCRIPT:\n\n{full_transcript_text}\n\n"
                            f"---\n\nNow produce the final synthesized answer."
                        ),
                    ),
                ],
                model=config.model,
                temperature=moderator.temperature,
                max_tokens=1500,
            )
            synthesis_text = completion.content
            for k, v in completion.usage.items():
                total_usage[k] = total_usage.get(k, 0) + v
        except ProviderError as e:
            synthesis_text = f"❌ Synthesis failed: {e}"

        transcript_md.append(f"\n---\n\n# 🏁 Final Synthesis\n\n{synthesis_text}\n")
        if total_usage:
            transcript_md.append(
                "\n<sub>Token usage: "
                + ", ".join(f"{k}={v}" for k, v in total_usage.items())
                + "</sub>"
            )

        yield (
            '<div class="status-banner success">✅ <strong>Debate complete.</strong></div>',
            synthesis_text,
            "\n".join(transcript_md),
            chips_html,
            config_json,
        )

    except ProviderError as e:
        yield (
            f'<div class="status-banner error">❌ Provider error: {e}</div>',
            synthesis_text,
            "\n".join(transcript_md),
            chips_html,
            "",
        )
    except Exception as e:
        yield (
            f'<div class="status-banner error">❌ Unexpected error: {type(e).__name__}: {e}</div>',
            synthesis_text,
            "\n".join(transcript_md),
            chips_html,
            "",
        )


def do_share(
    question: str,
    synthesis: str,
    transcript_md: str,
    config_json: str,
) -> str:
    """Create a shareable link for the current debate.

    Called by the '🔗 Share' button. Returns an HTML banner with the URL
    that the user can click to view the share in the standalone viewer.

    The URL is built from the DEBARE_SHARE_BASE_URL env var if set, otherwise
    defaults to http://127.0.0.1:8001 (the viewer's default port). To serve
    shares publicly, set DEBATE_SHARE_BASE_URL=https://your-domain.com and
    run the viewer behind a reverse proxy.
    """
    if not question or not synthesis:
        return '<div class="status-banner error">⚠️ Run a debate first before sharing.</div>'

    try:
        import json
        import re
        from debate_arena.shares import create_share
        from debate_arena.models import DebateResult, PersonaTurn

        config = json.loads(config_json) if config_json else {}

        # Parse turns back out of the markdown transcript for storage.
        turns: list[PersonaTurn] = []
        for m in re.finditer(
            r"^## (.+?) — Round (\d+) · (\w+)\n\n(.+?)(?=\n## |\n---|\Z)",
            transcript_md, re.MULTILINE | re.DOTALL,
        ):
            title, round_num, phase, content = m.groups()
            persona_id = title.split()[-1].lower().replace(" ", "-")
            turns.append(PersonaTurn(
                persona=persona_id, round=int(round_num), phase=phase, content=content.strip()
            ))

        result = DebateResult(
            question=question,
            transcript=turns,
            synthesis=synthesis,
            config=config,
            total_usage={},
        )
        share = create_share(result)
        base = os.environ.get("DEBATE_SHARE_BASE_URL", "http://127.0.0.1:8001")
        url = f"{base.rstrip('/')}/share/{share.id}"
        return (
            f'<div class="status-banner success">'
            f'🔗 <strong>Share link created!</strong> '
            f'<a href="{url}" target="_blank" class="share-link">View shared debate →</a>'
            f'<br><code class="share-url">{url}</code>'
            f'<br><small style="color: #475569;">Start the viewer with: <code>debate-viewer</code> (or <code>uvicorn debate_arena.viewer:app</code>)</small>'
            f'</div>'
        )
    except Exception as e:
        return f'<div class="status-banner error">❌ Share failed: {type(e).__name__}: {e}</div>'


# Add styles for the share link banner
SHARE_CSS = """
.share-link {
    display: inline-block;
    margin-left: 0.5rem;
    padding: 0.25rem 0.75rem;
    background: rgba(255, 255, 255, 0.5);
    border-radius: 6px;
    color: #065f46 !important;
    font-weight: 600;
    text-decoration: none;
}
.share-link:hover { background: white; }
.share-url {
    display: block;
    margin-top: 0.5rem;
    padding: 0.4rem 0.6rem;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 6px;
    font-size: 0.85rem;
    color: #065f46;
    word-break: break-all;
}
"""


CUSTOM_CSS = """
/* === RESET & BASE === */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif !important;
}

/* === HERO === */
.hero {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, transparent 100%);
    border-radius: 16px;
    margin-bottom: 1.5rem;
}
.hero h1 {
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.5rem !important;
    background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
.hero p {
    font-size: 1.1rem;
    color: #64748b;
    margin: 0 auto;
    max-width: 600px;
}
.hero a {
    color: #6366f1;
    text-decoration: none;
    font-weight: 600;
}

/* === STATUS BANNER === */
.status-banner {
    padding: 1rem 1.25rem;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 500;
    border: 1px solid;
    animation: fadeIn 0.2s ease-out;
}
.status-banner.info    { background: #eff6ff; color: #1e40af; border-color: #93c5fd; }
.status-banner.warn    { background: #fffbeb; color: #92400e; border-color: #fcd34d; }
.status-banner.synth   { background: #f0fdf4; color: #166534; border-color: #86efac; }
.status-banner.success { background: #ecfdf5; color: #065f46; border-color: #6ee7b7; }
.status-banner.error   { background: #fef2f2; color: #991b1b; border-color: #fca5a5; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

/* === PERSONA CHIPS === */
.chips-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.75rem 0 0.25rem;
}
.persona-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.85rem;
    background: color-mix(in srgb, var(--chip-color) 10%, white);
    color: var(--chip-color);
    border: 1px solid color-mix(in srgb, var(--chip-color) 30%, white);
    border-radius: 999px;
    font-size: 0.875rem;
    font-weight: 600;
    transition: all 0.15s;
}
.persona-chip:hover { transform: translateY(-1px); }
.chip-emoji { font-size: 1.1rem; }
.chip-tagline {
    color: #64748b;
    font-weight: 400;
    font-size: 0.8rem;
    margin-left: 0.25rem;
}
.empty-chips {
    color: #94a3b8;
    font-style: italic;
    padding: 0.5rem 0;
    font-size: 0.9rem;
}

/* === TABS === */
.tabs > .tab-nav > button {
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}

/* === PRESET CARDS === */
.preset-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.5rem 0 1rem;
}
.preset-card {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.85rem;
    background: white;
    color: var(--accent, #6366f1);
    border: 1.5px solid color-mix(in srgb, var(--accent, #6366f1) 30%, white);
    border-radius: 10px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
}
.preset-card:hover {
    background: color-mix(in srgb, var(--accent, #6366f1) 8%, white);
    border-color: var(--accent, #6366f1);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px color-mix(in srgb, var(--accent, #6366f1) 20%, transparent);
}
.preset-card:active,
.preset-card.clicked {
    background: color-mix(in srgb, var(--accent, #6366f1) 15%, white);
    transform: translateY(0);
}
.preset-emoji {
    font-size: 1.15rem;
    line-height: 1;
}
.preset-name {
    font-weight: 700;
}
.preset-desc {
    color: #64748b;
    font-weight: 400;
    font-size: 0.8rem;
    margin-left: 0.25rem;
}

/* === PRIMARY BUTTON === */
.primary-btn {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: 0.85rem 1.5rem !important;
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
    transition: all 0.2s !important;
}
.primary-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4) !important;
}

/* === SYNTHESIS CARD === */
.synthesis-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%);
    border: 1px solid #86efac;
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin: 0.5rem 0;
}
.synthesis-card h1, .synthesis-card h2, .synthesis-card h3 {
    color: #065f46 !important;
    margin-top: 0 !important;
}

/* === FOOTER === */
.footer {
    text-align: center;
    padding: 2rem 1rem 1rem;
    color: #94a3b8;
    font-size: 0.875rem;
    border-top: 1px solid #e2e8f0;
    margin-top: 2rem;
}
.footer a { color: #6366f1; text-decoration: none; font-weight: 500; }
.footer a:hover { text-decoration: underline; }
.footer .github-stars {
    display: inline-block;
    margin-left: 0.5rem;
    padding: 0.15rem 0.5rem;
    background: #fef3c7;
    color: #92400e;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* === LAYOUT === */
.section-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin: 1rem 0 0.5rem;
}

/* === RESPONSIVE === */
@media (max-width: 768px) {
    .hero h1 { font-size: 1.75rem !important; }
    .hero p { font-size: 0.95rem; }
    .chip-tagline { display: none; }
}
"""


PRESET_CLICK_JS = """
<script>
document.addEventListener('click', function(e) {
    const card = e.target.closest('.preset-card');
    if (!card) return;
    document.querySelectorAll('.preset-card.clicked').forEach(function(c) {
        c.classList.remove('clicked');
    });
    card.classList.add('clicked');
    const wrapper = card.closest('[id^="component-"]');
    if (wrapper) wrapper.click();
});
</script>
"""


def build_ui() -> gr.Blocks:
    """Construct the professional Gradio interface."""
    with gr.Blocks(
        title="🥊 Debate Arena — Multi-agent AI debates",
        fill_width=True,
    ) as demo:
        # === HERO ===
        gr.HTML(
            """
            <div class="hero">
                <h1>🥊 Debate Arena</h1>
                <p>Watch AI personas argue your question. Get a synthesized final answer
                from a moderator. Free, private, runs locally with Ollama.</p>
            </div>
            """
        )

        # === QUICK PRESETS ===
        if PRESETS:
            gr.Markdown('<div class="section-label">⚡ Quick presets — pick a starting point</div>')
            with gr.Row():
                preset_row = gr.HTML(value=render_preset_chips())
                # Hidden state to record the last selected preset
                active_preset = gr.State(value="")

        with gr.Row():
            # === LEFT: CONTROLS ===
            with gr.Column(scale=1, min_width=320):
                gr.Markdown('<div class="section-label">💭 Your question</div>')
                question = gr.Textbox(
                    label=None,
                    placeholder="e.g. Should I quit my job to start an AI company?",
                    lines=3,
                    show_label=False,
                )

                gr.Markdown('<div class="section-label">🎭 Pick your debaters</div>')
                personas = gr.CheckboxGroup(
                    choices=persona_choices_with_meta(),
                    value=DEFAULT_PERSONAS,
                    show_label=False,
                )
                # Live preview of selected chips
                chips_preview = gr.HTML(
                    value=render_persona_chips(DEFAULT_PERSONAS),
                )
                personas.change(
                    render_persona_chips,
                    inputs=[personas],
                    outputs=[chips_preview],
                )

                gr.Markdown('<div class="section-label">⚙️ Settings</div>')
                with gr.Group():
                    rounds = gr.Slider(
                        minimum=0,
                        maximum=3,
                        step=1,
                        value=1,
                        label="Crossfire rounds",
                        info="0 = opening only · 3 = extended back-and-forth",
                    )
                    use_demo = gr.Checkbox(
                        label="Demo mode (no API key needed)",
                        value=not any(
                            os.environ.get(k)
                            for k in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"]
                        ),
                    )
                with gr.Group():
                    with gr.Row():
                        provider_name = gr.Dropdown(
                            choices=["anthropic", "openai", "openrouter", "ollama", "stub"],
                            value="anthropic",
                            label="Provider",
                            scale=2,
                        )
                        model = gr.Textbox(
                            label="Model",
                            placeholder="default",
                            scale=3,
                        )

                run_btn = gr.Button(
                    "🥊 Start Debate",
                    variant="primary",
                    size="lg",
                    elem_classes="primary-btn",
                )

            # === RIGHT: RESULTS ===
            with gr.Column(scale=2, min_width=400):
                status = gr.HTML(
                    value='<div class="status-banner info">Ready. Pick a question and start a debate.</div>',
                )

                with gr.Tabs():
                    with gr.Tab("🏁 Final Answer"):
                        synthesis = gr.Markdown(
                            value="*Your synthesized final answer will appear here.*",
                            elem_classes="synthesis-card",
                        )
                    with gr.Tab("📜 Full Transcript"):
                        transcript = gr.Markdown(
                            value="*The full debate transcript will appear here.*",
                        )
                    with gr.Tab("💾 Export"):
                        gr.Markdown(
                            "Save the full debate as a Markdown file you can share, "
                            "publish, or paste into Notion/Confluence."
                        )
                        download_file = gr.File(
                            label="Download debate",
                            interactive=False,
                        )
                        with gr.Row():
                            export_md_btn = gr.Button("📋 Generate .md File", size="md")
                            copy_summary_btn = gr.Button("📑 Copy synthesis only", size="md")
                            share_btn = gr.Button("🔗 Share debate", size="md", variant="primary")
                        share_result = gr.HTML(value="")
                        # Hidden state: stores debate config so we can recreate DebateResult for sharing
                        share_config = gr.State(value="")

        # === EXAMPLES ===
        gr.Examples(
            examples=[
                [
                    "Should I quit my job to start an AI company?",
                    DEFAULT_PERSONAS,
                    1,
                    "anthropic",
                    "",
                ],
                [
                    "Best stack for a SaaS MVP in 2026?",
                    ["skeptic", "engineer", "strategist"],
                    2,
                    "anthropic",
                    "",
                ],
                [
                    "Will AI replace programmers in 5 years?",
                    ["skeptic", "optimist", "engineer", "strategist"],
                    2,
                    "openrouter",
                    "anthropic/claude-3.5-sonnet",
                ],
                [
                    "Should we launch a crypto token?",
                    ["hacker", "regulator", "customer"],
                    1,
                    "ollama",
                    "",
                ],
                [
                    "Best investment for a 30-year-old with $50k?",
                    ["trader", "first-principles", "philosopher"],
                    2,
                    "anthropic",
                    "",
                ],
            ],
            inputs=[question, personas, rounds, provider_name, model],
            label="💡 Try one of these",
        )

        # === FOOTER ===
        gr.HTML(
            """
            <div class="footer">
                Built with Python + Gradio ·
                <a href="https://github.com/Aryan0707/debate-arena" target="_blank">
                    View on GitHub
                </a>
                <span class="github-stars">⭐ Open source</span>
                <br>
                Supports Anthropic Claude · OpenAI · OpenRouter · Ollama · Demo mode
            </div>
            """
        )

        # === EVENT WIRING ===
        # Preset click handler: when a preset card is clicked, capture its
        # data-preset-id attribute, pass it to apply_preset, and update the
        # question/personas/rounds/banner fields.
        preset_row.click(
            apply_preset,
            inputs=[active_preset],
            outputs=[question, personas, rounds, status, active_preset],
            js="""
            (currentActive) => {
                const clicked = document.querySelector('.preset-card.clicked');
                if (!clicked) return [''];
                return [clicked.getAttribute('data-preset-id')];
            }
            """,
        )

        run_btn.click(
            run_debate,
            inputs=[question, personas, rounds, provider_name, model, use_demo],
            outputs=[status, synthesis, transcript, chips_preview, share_config],
        )

        export_md_btn.click(
            lambda md: _save_md(md),
            inputs=[transcript],
            outputs=[download_file],
        )
        copy_summary_btn.click(
            lambda syn: syn,
            inputs=[synthesis],
            outputs=[synthesis],
            js="(s) => { navigator.clipboard.writeText(s); return s; }",
        )

        share_btn.click(
            do_share,
            inputs=[question, synthesis, transcript, share_config],
            outputs=[share_result],
        )

    return demo


def _save_md(md: str) -> str:
    """Save the markdown transcript to a temp file and return its path."""
    path = Path("/tmp/debate-arena-export.md")
    path.write_text(md or "")
    return str(path)


def main() -> int:
    p = argparse.ArgumentParser(description="Launch the debate arena web UI")
    p.add_argument("--port", type=int, default=7860, help="Port to listen on")
    p.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    p.add_argument("--share", action="store_true", help="Create a public gradio.live URL")
    args = p.parse_args()

    demo = build_ui()
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        css=CUSTOM_CSS,
        head=PRESET_CLICK_JS,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
