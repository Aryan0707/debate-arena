"""Stub provider that works offline with no API key. Used for demo mode and tests."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from debate_arena.providers.base import Completion, Message

_STUB_OPENINGS: dict[str, str] = {
    "skeptic": (
        "From the skeptic's chair: the question '{question}' looks simpler than it is. "
        "The most common failure mode here is {failure_mode}. I'd want to see evidence "
        "of {evidence} before being convinced. What's the worst plausible outcome, and "
        "how would we detect it early?"
    ),
    "optimist": (
        "Looking at '{question}' through an optimist lens — the upside here is real. "
        "We've seen comparable bets pay off {payoff_evidence}x when the conditions are "
        "right. The cost of inaction is being outpaced by {competitor_pressure}, and "
        "this is one of those asymmetric calls where the upside dominates the downside. "
        "The question isn't whether to act, it's how fast."
    ),
    "engineer": (
        "On '{question}' from an engineering standpoint: ship it in 3 phases. "
        "Phase 1 (1-2 weeks): {phase1}. Phase 2 (1 month): {phase2}. "
        "Phase 3 (quarter): {phase3}. Total cost ~{cost}. "
        "Scaling cliff appears around {scale}, and the maintenance burden is "
        "{maintenance} — manageable. The 80/20 is {biggest_leverage}."
    ),
    "strategist": (
        "Zooming out on '{question}': the more interesting question is what world "
        "we're in 2-3 years out. If this works, {scenario}. If it doesn't, "
        "{alt_scenario}. The non-obvious dependency is {dependency} — locking that in "
        "early matters more than the visible feature. Competitor response will be "
        "{response_pattern}, so we need to be {positioning}."
    ),
    "moderator": (
        "Synthesis on '{question}':\n\n"
        "**Bottom line:** {verdict}\n\n"
        "The debate surfaced strong arguments on both sides. The skeptic's concern "
        "about {skeptic_concern} is the most important risk to mitigate, but the "
        "optimist is right that the cost of inaction is being underestimated. The "
        "engineer's 3-phase plan is the right path, with {caveat}.\n\n"
        "**Concrete next steps:**\n{steps}\n\n"
        "**What would change my mind:** {falsifier}"
    ),
}

_FILLERS = {
    "failure_mode": [
        "confusing effort with progress",
        "shipping a solution to the wrong problem",
        "underestimating the second-order effects",
    ],
    "evidence": [
        "three independent case studies showing this works",
        "real user data, not just theory",
        "a working prototype under real conditions",
    ],
    "payoff_evidence": ["5", "10", "20"],
    "competitor_pressure": [
        "the market moving without us",
        "well-funded incumbents shipping similar features",
        "shifting customer expectations",
    ],
    "phase1": [
        "a thin slice you can demo to 5 users",
        "scoping the data model and riskiest integration",
        "a clickable prototype that proves the UX",
    ],
    "phase2": [
        "the full vertical slice with one paying customer",
        "production-ready infrastructure for the core path",
        "the analytics and feedback loop that drives iteration",
    ],
    "phase3": [
        "scaling, observability, and the second use case",
        "expanding to the next segment based on Phase 2 learnings",
        "the platform play that unlocks long-term compounding",
    ],
    "cost": [
        "1 engineer-month for the MVP",
        "$20k infra for the first year",
        "3 engineer-months including ops overhead",
    ],
    "scale": [
        "10k concurrent users",
        "100GB of customer data",
        "the 5th integration partner",
    ],
    "maintenance": [
        "small",
        "moderate — one engineer can hold it",
        "moderate, with a quarterly review",
    ],
    "biggest_leverage": [
        "the data flywheel that compounds",
        "the distribution channel that opens up after Phase 1",
        "the user research that de-risks Phase 2",
    ],
    "scenario": [
        "we become the default in our category",
        "we have to rebuild the platform under pressure from incumbents",
        "the market consolidates around 2-3 players and we're one of them",
    ],
    "alt_scenario": [
        "we get squeezed by a well-funded incumbent",
        "regulatory shift forces a redesign",
        "we plateau and need a second act",
    ],
    "dependency": [
        "the data partnerships",
        "the API contracts with the top 3 platforms",
        "the design talent we can recruit",
    ],
    "response_pattern": [
        "fast follower with deeper distribution",
        "defensive bundling",
        "regulatory capture",
    ],
    "positioning": [
        "first to the second wave of users",
        "the open standard they have to support",
        "the platform others build on",
    ],
    "verdict": [
        "Do it, but in the engineer-shaped sequence.",
        "Hold off and gather the data the skeptic wants first.",
        "Do a small bet that preserves optionality.",
    ],
    "skeptic_concern": [
        "the failure mode the skeptic flagged",
        "the cost being underestimated",
        "the timeline slippage risk",
    ],
    "caveat": [
        "an explicit kill criterion at the end of Phase 1",
        "a budget cap that forces a real decision",
        "a measurable success metric, not vibes",
    ],
    "steps": [
        "1. Scope the prototype this week\n2. Run it past 5 target users\n3. Decide by [date]",
        "1. Build Phase 1 in 2 weeks\n2. Measure one hard metric\n3. Kill or continue based on it",
        "1. Lock the dependency first\n2. Then ship the wedge\n3. Re-evaluate at the gate",
    ],
    "falsifier": [
        "If the prototype doesn't move the metric, the thesis is wrong.",
        "If we can't recruit the design talent in 60 days, we revise the plan.",
        "If competitors ship a credible alternative first, we pivot to a defensible niche.",
    ],
}


def _fill(template: str) -> str:
    """Substitute {key} placeholders with random fillers."""
    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key == "question":
            return match.string[match.start():match.end()]  # leave as-is, caller fills
        choices = _FILLERS.get(key)
        if not choices:
            return match.group(0)
        return random.choice(choices)
    return re.sub(r"\{(\w+)\}", repl, template)


@dataclass
class StubProvider:
    """Offline provider that generates plausible-looking but synthetic debate text.

    Useful for:
    - Trying out the CLI without an API key
    - Testing the orchestration logic
    - Demoing the concept

    Not actually useful for real answers — the content is templated and randomized.
    """

    name: str = "stub"
    default_model: str = "stub-v1"

    def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Completion:
        # Extract the persona from the system prompt.
        # Match the self-introduction pattern "You are the X" / "You are X" which
        # appears at the start of every persona prompt and uniquely identifies
        # which persona is speaking. This avoids false matches when a persona's
        # system prompt happens to mention other personas.
        import re

        system = next((m.content for m in messages if m.role == "system"), "")
        user = next((m.content for m in messages if m.role == "user"), "")

        persona_id = "moderator"  # safe fallback
        m = re.search(r"\byou are (?:the )?(\w+)\b", system, re.IGNORECASE)
        if m:
            candidate = m.group(1).lower()
            if candidate in _STUB_OPENINGS:
                persona_id = candidate

        # Extract the original question from the user message.
        m = re.search(r"QUESTION:\s*(.+?)(?:\n|$)", user)
        question = m.group(1).strip() if m else user[:120]

        # For rebuttal turns, append a short "engagement" line so it doesn't look
        # identical to the opening.
        rebuttal = "other personas have said" in user.lower()
        template = _STUB_OPENINGS[persona_id]
        text = _fill(template).format(question=question)

        if rebuttal:
            text += (
                "\n\nRebuttal: I disagree with the framing from the others. "
                f"The strongest point against me is that {random.choice(_FILLERS['failure_mode'])}, "
                f"but my response is that {random.choice(_FILLERS['phase1'])} mitigates that risk. "
                "I'd want us to converge on the metric we're optimizing, not the narrative."
            )

        return Completion(content=text, model=self.default_model, usage={"stub": 1})
