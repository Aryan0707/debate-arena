"""Example: export a debate as a publishable blog post.

After running a debate, the DebateResult.to_markdown() output is a clean
narrative that you can drop straight into a blog, Notion page, or wiki.
"""

from pathlib import Path

from debate_arena import DebateArena, DebateConfig
from debate_arena.providers import StubProvider

# A real question worth debating
question = "Should an early-stage startup build with no-code tools or invest in custom code from day 1?"

arena = DebateArena(
    provider=StubProvider(),  # swap for AnthropicProvider(model="claude-3-5-sonnet-20241022")
    stream=False,             # don't print the panels, just run silently
)

config = DebateConfig(
    question=question,
    personas=["skeptic", "optimist", "engineer", "strategist"],
    rounds=2,                 # two crossfire rounds for a deeper debate
    model=None,
)

result = arena.run(config)

# Write the full transcript
Path("blog_post_source.md").write_text(result.to_markdown())
print(f"Done. {len(result.transcript)} turns, synthesis {len(result.synthesis or '')} chars.")
print("Open blog_post_source.md to see the full debate.")
