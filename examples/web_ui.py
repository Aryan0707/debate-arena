"""Gradio web UI for the debate arena.

Run with:
    python examples/web_ui.py                    # demo mode (no API key)
    ANTHROPIC_API_KEY=*** python examples/web_ui.py
    python examples/web_ui.py --share            # create a public gradio.live URL
    python examples/web_ui.py --port 8080        # change port

The UI lets you:
- Type a question
- Pick personas (multi-select)
- Pick provider + model
- Set crossfire rounds
- Watch the debate stream panel-by-panel
- Download the full debate as markdown
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
from debate_arena.personas import PERSONAS_DIR
from debate_arena.providers import detect_provider, get_provider

AVAILABLE_PERSONAS = sorted(p.stem for p in PERSONAS_DIR.glob("*.yaml"))
DEFAULT_PERSONAS = ["skeptic", "optimist", "engineer"]


def run_debate(
    question: str,
    personas: list[str],
    rounds: int,
    provider_name: str,
    model: str,
    use_demo: bool,
):
    """Stream the debate as it happens, yielding (panel_text, synthesis, md) tuples."""
    if not question or not question.strip():
        yield "⚠️ Please enter a question.", "", ""
        return
    if not personas:
        yield "⚠️ Please select at least one persona.", "", ""

    # Demo mode wins.
    if use_demo:
        provider_name = "stub"

    try:
        provider = get_provider(provider_name, model=model or None)
    except Exception as e:
        yield f"❌ Could not set up provider: {e}", "", ""
        return

    arena = DebateArena(provider=provider, stream=False)

    config = DebateConfig(
        question=question,
        personas=personas,
        rounds=rounds,
        model=model or None,
        provider=detect_provider(provider_name),
    )

    transcript_md: list[str] = [f"# Debate: {question}\n"]
    synthesis_text = ""
    status = "🥊 **Opening statements...**"
    yield status, "", "\n".join(transcript_md)

    # Run the debate turn-by-turn, streaming each one to the UI.
    try:
        from debate_arena.personas import load_personas
        from debate_arena.providers.base import Message, ProviderError

        personas_objs = load_personas(config.personas)
        transcript: list = []
        total_usage: dict = {}

        # Phase 1: openings
        for persona in personas_objs:
            status = f"🥊 **{persona.name}** is delivering opening statement..."
            yield status, "", "\n".join(transcript_md)

            turn = arena._run_turn(
                persona=persona,
                question=config.question,
                prior_turns=[],
                round_num=1,
                phase="opening",
                model=config.model,
            )
            transcript.append(turn)
            transcript_md.append(f"\n## {turn.persona.title()} — Round 1 (opening)\n\n{turn.content}\n")
            yield status, "", "\n".join(transcript_md)
            for k, v in turn.usage.items():
                total_usage[k] = total_usage.get(k, 0) + v

        # Phase 2: crossfire
        for r in range(1, config.rounds + 1):
            status = f"⚔️  **Crossfire — round {r}**"
            yield status, "", "\n".join(transcript_md)

            for persona in personas_objs:
                status = f"⚔️  **{persona.name}** is rebutting (round {r})..."
                yield status, "", "\n".join(transcript_md)

                others = [t for t in transcript if t.persona != persona.id]
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
                transcript.append(turn)
                transcript_md.append(
                    f"\n## {turn.persona.title()} — Round {r} (rebuttal)\n\n{turn.content}\n"
                )
                yield status, "", "\n".join(transcript_md)
                for k, v in turn.usage.items():
                    total_usage[k] = total_usage.get(k, 0) + v

        # Phase 3: synthesis
        status = "🏁 **Moderator is synthesizing the final answer...**"
        yield status, "", "\n".join(transcript_md)

        try:
            moderator = load_personas([config.moderator])[0]
        except FileNotFoundError:
            moderator = load_personas(["engineer"])[0]

        full_transcript_text = "\n\n---\n\n".join(
            f"[{t.persona} — round {t.round} · {t.phase}]\n{t.content}" for t in transcript
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
        status = "✅ **Debate complete.**"
        yield status, synthesis_text, "\n".join(transcript_md)

    except ProviderError as e:
        yield f"❌ Provider error: {e}", synthesis_text, "\n".join(transcript_md)
    except Exception as e:
        yield f"❌ Unexpected error: {type(e).__name__}: {e}", synthesis_text, "\n".join(transcript_md)


def build_ui() -> gr.Blocks:
    """Construct the Gradio interface."""
    with gr.Blocks(
        title="🥊 Debate Arena",
    ) as demo:
        gr.Markdown(
            """
            # 🥊 Multi-Claude Debate Arena
            Type a question. Watch AI personas with different viewpoints argue it out.
            Get a synthesized final answer from the moderator.
            """
        )

        with gr.Row():
            with gr.Column(scale=2):
                question = gr.Textbox(
                    label="Question to debate",
                    placeholder="e.g. Should I quit my job to start an AI company?",
                    lines=3,
                )
                with gr.Row():
                    personas = gr.CheckboxGroup(
                        choices=AVAILABLE_PERSONAS,
                        value=DEFAULT_PERSONAS,
                        label="Personas",
                        info="Each persona brings a different lens.",
                    )
                with gr.Row():
                    rounds = gr.Slider(
                        minimum=0, maximum=3, step=1, value=1,
                        label="Crossfire rounds",
                        info="0 = opening statements only, 3 = a long back-and-forth",
                    )
                with gr.Row():
                    use_demo = gr.Checkbox(
                        label="Demo mode (no API key needed)",
                        value=not any(
                            os.environ.get(k) for k in
                            ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"]
                        ),
                    )
                with gr.Row():
                    provider_name = gr.Dropdown(
                        choices=["anthropic", "openai", "openrouter", "stub"],
                        value="anthropic",
                        label="Provider",
                    )
                    model = gr.Textbox(
                        label="Model (optional)",
                        placeholder="leave blank for provider default",
                    )
                run_btn = gr.Button("🥊 Start Debate", variant="primary", size="lg")

            with gr.Column(scale=3):
                status = gr.Markdown("Ready.", elem_classes="status")
                with gr.Tab("🏁 Final Synthesis"):
                    synthesis = gr.Markdown()
                with gr.Tab("📜 Full Transcript"):
                    transcript = gr.Markdown(elem_classes="transcript")
                with gr.Tab("💾 Download"):
                    download_file = gr.File(label="Download debate as Markdown")
                    download_btn = gr.Button("Generate Markdown File")
                    download_btn.click(
                        lambda md: str(Path("/tmp/debate.md").write_text(md)) and "/tmp/debate.md"
                        or "/tmp/debate.md",
                        inputs=[transcript],
                        outputs=[download_file],
                    )

        run_btn.click(
            run_debate,
            inputs=[question, personas, rounds, provider_name, model, use_demo],
            outputs=[status, synthesis, transcript],
        )

        # Examples
        gr.Examples(
            examples=[
                ["Should I quit my job to start an AI company?", DEFAULT_PERSONAS, 1, "anthropic", ""],
                ["What's the best stack for a SaaS MVP in 2026?",
                 ["skeptic", "engineer", "strategist"], 2, "anthropic", ""],
                ["Will AI replace programmers in 5 years?",
                 ["skeptic", "optimist", "engineer", "strategist"], 2, "openrouter", "anthropic/claude-3.5-sonnet"],
                ["Is Web3 dead?", DEFAULT_PERSONAS, 1, "anthropic", ""],
            ],
            inputs=[question, personas, rounds, provider_name, model],
        )

    return demo


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
        theme=gr.themes.Soft(primary_hue="indigo"),
        css="""
        .status { font-size: 1.1em; padding: 0.5em; }
        .transcript { font-family: ui-monospace, monospace; }
        """,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
