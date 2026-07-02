"""CLI entry point for the debate arena."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from debate_arena import DebateArena
from debate_arena.config import DebateConfig
from debate_arena.providers import detect_provider, get_provider


@click.command()
@click.argument("question", required=False)
@click.option(
    "-p",
    "--provider",
    type=click.Choice(
        ["anthropic", "openai", "openrouter", "ollama", "stub"], case_sensitive=False
    ),
    default=None,
    help="LLM provider (default: auto-detect from env vars, then ollama if running, then stub).",
)
@click.option(
    "-m",
    "--model",
    default=None,
    help="Model name (provider-specific). Defaults to provider's default model.",
)
@click.option(
    "-r",
    "--rounds",
    type=int,
    default=1,
    show_default=True,
    help="Number of crossfire rebuttal rounds.",
)
@click.option(
    "--personas",
    default="skeptic,optimist,engineer",
    show_default=True,
    help="Comma-separated list of persona IDs to use.",
)
@click.option(
    "--moderator",
    default="moderator",
    show_default=True,
    help="Persona ID to use for the synthesis phase.",
)
@click.option(
    "--no-synthesis",
    is_flag=True,
    help="Skip the synthesis phase, just show the debate.",
)
@click.option(
    "--demo",
    is_flag=True,
    help="Run in demo mode (no API key, local stub provider).",
)
@click.option(
    "--no-stream",
    is_flag=True,
    help="Disable streaming output (useful for piping).",
)
@click.option(
    "-e",
    "--export",
    "export_path",
    type=click.Path(),
    default=None,
    help="Export the full debate to a markdown file.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress the live debate, print only the final synthesis.",
)
def main(
    question: str | None,
    provider: str | None,
    model: str | None,
    rounds: int,
    personas: str,
    moderator: str,
    no_synthesis: bool,
    demo: bool,
    no_stream: bool,
    export_path: str | None,
    quiet: bool,
) -> None:
    """Run a multi-agent debate on QUESTION.

    Examples:

        debate "Should I quit my job?"

        debate --demo "What's the meaning of life?"

        debate -p openrouter -m anthropic/claude-3.5-sonnet "Best stack for SaaS MVP?"
    """
    if not question:
        click.echo("Error: QUESTION argument is required.\n", err=True)
        click.echo("Usage: debate 'Your question here'\n", err=True)
        sys.exit(2)

    persona_list = [p.strip() for p in personas.split(",") if p.strip()]

    # Demo mode overrides everything.
    if demo:
        provider = "stub"

    try:
        prov = get_provider(provider, model=model)
    except Exception as e:
        click.echo(f"Error setting up provider: {e}", err=True)
        click.echo(
            "\nTip: set ANTHROPIC_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY,\n"
            "or use --demo for offline mode.",
            err=True,
        )
        sys.exit(1)

    if quiet:
        # Patch the console to be silent.
        from rich.console import Console
        prov_console = Console(file=open("/dev/null", "w"))
    else:
        prov_console = None

    arena = DebateArena(provider=prov, console=prov_console, stream=not no_stream)

    config = DebateConfig(
        question=question,
        personas=persona_list,
        rounds=rounds,
        moderator=moderator,
        include_synthesis=not no_synthesis,
        model=model,
        provider=detect_provider(provider),
    )

    result = arena.run(config)

    if export_path:
        Path(export_path).write_text(result.to_markdown())
        click.echo(f"\n📄 Exported to {export_path}")

    if quiet and result.synthesis:
        click.echo(result.synthesis)


if __name__ == "__main__":  # pragma: no cover
    main()
