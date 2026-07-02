"""Example: use the debate arena as a Python library.

Run with:
    ANTHROPIC_API_KEY=*** python examples/run_python_api.py "Your question"

Or in demo mode (no API key):
    python examples/run_python_api.py --demo "Your question"
"""

from __future__ import annotations

import argparse
import sys

from debate_arena import DebateArena, DebateConfig
from debate_arena.providers import detect_provider, get_provider


def main() -> int:
    p = argparse.ArgumentParser(description="Run a debate from Python")
    p.add_argument("question", help="The question to debate")
    p.add_argument(
        "--provider",
        choices=["anthropic", "openai", "openrouter", "stub"],
        default=None,
    )
    p.add_argument("--model", default=None)
    p.add_argument("--rounds", type=int, default=1)
    p.add_argument("--personas", default="skeptic,optimist,engineer")
    p.add_argument("--export", default=None, help="Markdown export path")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()

    if args.demo:
        args.provider = "stub"

    provider = get_provider(args.provider, model=args.model)
    arena = DebateArena(provider=provider)

    personas = [x.strip() for x in args.personas.split(",") if x.strip()]
    config = DebateConfig(
        question=args.question,
        personas=personas,
        rounds=args.rounds,
        model=args.model,
        provider=detect_provider(args.provider),
    )

    result = arena.run(config)

    if args.export:
        from pathlib import Path

        Path(args.export).write_text(result.to_markdown())
        print(f"\nExported to {args.export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
