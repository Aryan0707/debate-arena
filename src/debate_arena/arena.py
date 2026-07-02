"""The DebateArena orchestrator: runs the multi-phase debate."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from debate_arena.config import DebateConfig
from debate_arena.models import DebateResult, PersonaTurn
from debate_arena.personas import Persona, load_personas
from debate_arena.providers.base import Message, Provider, ProviderError

_console = Console()


class DebateArena:
    """Runs a structured multi-agent debate.

    Phases:
        1. Opening — each persona states their position on the question.
        2. Crossfire — `rounds` rounds of rebuttal. Each persona sees the
           others' most recent statements and responds.
        3. Synthesis — moderator persona reads the full transcript and
           produces the final answer.
    """

    def __init__(
        self,
        provider: Provider,
        *,
        console: Console | None = None,
        stream: bool = True,
    ) -> None:
        self.provider = provider
        self.console = console or _console
        self.stream = stream

    def _run_turn(
        self,
        *,
        persona: Persona,
        question: str,
        prior_turns: list[str],
        round_num: int,
        phase: str,
        model: str | None = None,
    ) -> PersonaTurn:
        messages: list[Message] = [
            Message(role="system", content=persona.system_prompt),
            Message(
                role="user",
                content=persona.render_user_message(question, prior_turns or None),
            ),
        ]
        try:
            completion = self.provider.complete(
                messages,
                model=model,
                temperature=persona.temperature,
                max_tokens=1024,
            )
        except ProviderError as e:
            raise ProviderError(f"{persona.name} ({phase}, round {round_num}) failed: {e}") from e

        return PersonaTurn(
            persona=persona.id,
            round=round_num,
            phase=phase,
            content=completion.content,
            usage=completion.usage,
        )

    def _stream_panel(self, persona: Persona, content: str, phase: str, round_num: int) -> None:
        title = f"🥊 {persona.name} — {phase} · round {round_num}"
        if self.stream:
            self.console.print(
                Panel(Text(content, style="white"), title=title, border_style="cyan")
            )
        else:
            self.console.log(f"[{persona.id}] {content[:200]}…")

    def run(self, config: DebateConfig) -> DebateResult:
        """Execute the full debate and return the result."""
        personas = load_personas(config.personas)
        if not personas:
            raise ValueError("at least one persona is required")

        transcript: list[PersonaTurn] = []
        total_usage: dict[str, int] = {}

        # === Phase 1: openings ===
        self.console.rule("[bold cyan]🥊 OPENING STATEMENTS")
        for persona in personas:
            turn = self._run_turn(
                persona=persona,
                question=config.question,
                prior_turns=[],
                round_num=1,
                phase="opening",
                model=config.model,
            )
            transcript.append(turn)
            self._stream_panel(persona, turn.content, "opening", 1)
            for k, v in turn.usage.items():
                total_usage[k] = total_usage.get(k, 0) + v

        # === Phase 2: crossfire ===
        for r in range(1, config.rounds + 1):
            self.console.rule(f"[bold yellow]⚔️  CROSSFIRE — ROUND {r}")
            # Each persona rebuts, having seen the others' latest statements.
            for persona in personas:
                # Build the prior context from this persona's POV: skip their own
                # last turn, include the others'.
                others = [t for t in transcript if t.persona != persona.id]
                # Only show the most recent round's content to keep context focused.
                recent = others[-len(personas) :] if len(others) >= len(personas) else others
                prior_text = [f"[{t.persona}]\n{t.content}" for t in recent]
                turn = self._run_turn(
                    persona=persona,
                    question=config.question,
                    prior_turns=prior_text,
                    round_num=r,
                    phase="rebuttal",
                    model=config.model,
                )
                transcript.append(turn)
                self._stream_panel(persona, turn.content, "rebuttal", r)
                for k, v in turn.usage.items():
                    total_usage[k] = total_usage.get(k, 0) + v

        # === Phase 3: synthesis ===
        synthesis: str | None = None
        if config.include_synthesis:
            self.console.rule("[bold green]🏁 SYNTHESIS")
            try:
                moderator = load_personas([config.moderator])[0]
            except FileNotFoundError:
                self.console.print(
                    f"[yellow]moderator persona '{config.moderator}' not found, "
                    f"using engineer as fallback[/yellow]"
                )
                moderator = load_personas(["engineer"])[0]

            full_transcript_text = "\n\n---\n\n".join(
                f"[{t.persona} — round {t.round} · {t.phase}]\n{t.content}" for t in transcript
            )
            synth_messages: list[Message] = [
                Message(role="system", content=moderator.system_prompt),
                Message(
                    role="user",
                    content=(
                        f"QUESTION: {config.question}\n\n"
                        f"FULL DEBATE TRANSCRIPT:\n\n{full_transcript_text}\n\n"
                        f"---\n\nNow produce the final synthesized answer."
                    ),
                ),
            ]
            try:
                completion = self.provider.complete(
                    synth_messages,
                    model=config.model,
                    temperature=moderator.temperature,
                    max_tokens=1500,
                )
                synthesis = completion.content
                for k, v in completion.usage.items():
                    total_usage[k] = total_usage.get(k, 0) + v
                self.console.print(
                    Panel(
                        Text(synthesis, style="white"),
                        title="🏁 FINAL SYNTHESIS",
                        border_style="green",
                    )
                )
            except ProviderError as e:
                self.console.print(f"[red]synthesis failed: {e}[/red]")
                synthesis = None

        return DebateResult(
            question=config.question,
            transcript=transcript,
            synthesis=synthesis,
            config={
                "personas": config.personas,
                "rounds": config.rounds,
                "moderator": config.moderator,
                "model": config.model,
                "provider": self.provider.name,
            },
            total_usage=total_usage,
        )
