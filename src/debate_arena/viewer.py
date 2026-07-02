"""Public, read-only viewer for shared debates.

Serves a clean, single-page HTML view of a shared debate at /share/{id}.
Anyone with the URL can view it — no auth, no account, no API key.

The viewer renders the full transcript and synthesis with the same
PERSONA_META color scheme as the main web UI, so shared links feel
like first-class pages.

Run standalone:
    uvicorn debate_arena.viewer:app --host 0.0.0.0 --port 8000

Or it's auto-mounted by the main Gradio web UI at /share/{id}.
"""

from __future__ import annotations

import html
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from debate_arena.shares import get_share, list_shares

# Same persona metadata as the main web UI so the look is consistent.
PERSONA_META = {
    "skeptic":          {"emoji": "🔍", "tagline": "Pokes holes, demands evidence",       "color": "#ef4444"},
    "optimist":         {"emoji": "🚀", "tagline": "Sees upside, advocates bold action",   "color": "#f59e0b"},
    "engineer":         {"emoji": "🔨", "tagline": "Feasibility, cost, scaling",           "color": "#3b82f6"},
    "strategist":       {"emoji": "♟️", "tagline": "Long-term, game theory, 2nd order",     "color": "#8b5cf6"},
    "moderator":        {"emoji": "⚖️", "tagline": "Synthesizes the final answer",         "color": "#10b981"},
    "hacker":           {"emoji": "💻", "tagline": "Leverage, exploits, asymmetric plays", "color": "#ec4899"},
    "regulator":        {"emoji": "📜", "tagline": "Compliance, legal risk, policy",       "color": "#6366f1"},
    "philosopher":      {"emoji": "🏛️", "tagline": "Ethics, meaning, reframes the Q",      "color": "#14b8a6"},
    "trader":           {"emoji": "📈", "tagline": "Expected value, position sizing",      "color": "#84cc16"},
    "customer":         {"emoji": "👤", "tagline": "Voice of the actual end user",         "color": "#f97316"},
    "first-principles": {"emoji": "🧬", "tagline": "Strips assumptions, demands rigor",    "color": "#06b6d4"},
}


app = FastAPI(
    title="Debate Arena — Share Viewer",
    description="Public, read-only viewer for shared AI debates",
    docs_url=None,
    redoc_url=None,
)


def _format_turn(turn: dict[str, Any]) -> str:
    """Render a single turn as an HTML card."""
    persona = turn.get("persona", "unknown")
    meta = PERSONA_META.get(persona, {"emoji": "•", "color": "#64748b", "tagline": ""})
    name = persona.replace("-", " ").title()
    content = html.escape(turn.get("content", "")).replace("\n\n", "</p><p>").replace("\n", "<br>")
    round_num = turn.get("round", 1)
    phase = turn.get("phase", "opening")

    return f"""
    <article class="turn" style="--accent: {meta['color']}">
      <header>
        <span class="persona-emoji">{meta['emoji']}</span>
        <div class="persona-info">
          <div class="persona-name">{name}</div>
          <div class="persona-meta">Round {round_num} · {phase}</div>
        </div>
      </header>
      <div class="turn-content"><p>{content}</p></div>
    </article>
    """


def _format_synthesis(text: str | None) -> str:
    """Render the synthesis section as a green-tinted callout."""
    if not text:
        return ""
    # Light markdown rendering: just preserve paragraph breaks and bold
    escaped = html.escape(text)
    escaped = escaped.replace("\n\n", "</p><p>").replace("\n", "<br>")
    # **bold** → <strong>
    import re
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return f"""
    <section class="synthesis">
      <h2>🏁 Final Synthesis</h2>
      <div class="synthesis-body"><p>{escaped}</p></div>
    </section>
    """


SHARED_VIEWER_CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
    margin: 0;
    background: #f8fafc;
    color: #0f172a;
    line-height: 1.65;
}
.container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
}
.hero {
    text-align: center;
    padding: 2rem 1rem 1.5rem;
    background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, transparent 100%);
    border-radius: 16px;
    margin-bottom: 2rem;
}
.hero h1 {
    font-size: 2.25rem;
    font-weight: 800;
    margin: 0 0 0.5rem;
    background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
.hero .question {
    font-size: 1.15rem;
    color: #475569;
    margin: 1rem auto 0.5rem;
    max-width: 640px;
    font-weight: 500;
}
.hero .meta {
    color: #94a3b8;
    font-size: 0.85rem;
    margin-top: 0.5rem;
}
.turn {
    background: white;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid var(--accent, #64748b);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.turn header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}
.persona-emoji {
    font-size: 1.75rem;
    width: 2.5rem;
    height: 2.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--accent, #64748b) 12%, white);
    border-radius: 10px;
    flex-shrink: 0;
}
.persona-name {
    font-weight: 700;
    font-size: 1rem;
    color: #0f172a;
}
.persona-meta {
    font-size: 0.8rem;
    color: #94a3b8;
    font-weight: 500;
}
.turn-content {
    color: #334155;
    font-size: 0.97rem;
}
.turn-content p { margin: 0 0 0.5rem; }
.turn-content p:last-child { margin-bottom: 0; }
.synthesis {
    background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%);
    border: 1px solid #86efac;
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin: 1.5rem 0;
}
.synthesis h2 {
    color: #065f46;
    margin: 0 0 1rem;
    font-size: 1.4rem;
}
.synthesis-body p { margin: 0 0 0.75rem; }
.synthesis-body p:last-child { margin-bottom: 0; }
.footer {
    text-align: center;
    color: #94a3b8;
    font-size: 0.875rem;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e2e8f0;
}
.footer a {
    color: #6366f1;
    text-decoration: none;
    font-weight: 600;
}
.footer a:hover { text-decoration: underline; }
.section-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin: 1.5rem 0 0.75rem;
}
@media (max-width: 640px) {
    .container { padding: 1rem 0.75rem 2rem; }
    .hero h1 { font-size: 1.75rem; }
    .turn { padding: 1rem; }
    .synthesis { padding: 1.25rem; }
}
"""


@app.get("/share/{share_id}", response_class=HTMLResponse)
def view_share(share_id: str) -> str:
    """Public HTML view of a shared debate."""
    share = get_share(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or expired")

    import datetime as _dt
    created = _dt.datetime.fromtimestamp(share.created_at, tz=_dt.timezone.utc)
    created_str = created.strftime("%B %d, %Y at %H:%M UTC")

    turn_html = "\n".join(_format_turn(t) for t in share.transcript)
    synth_html = _format_synthesis(share.synthesis)

    n_personas = len({t.get("persona") for t in share.transcript if t.get("persona") != "moderator"})
    n_rounds = max((t.get("round", 1) for t in share.transcript), default=1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(share.question[:80])} — Debate Arena</title>
    <meta property="og:title" content="{html.escape(share.question[:80])}">
    <meta property="og:description" content="A multi-persona AI debate. {n_personas} personas, {n_rounds} round{'s' if n_rounds > 1 else ''}.">
    <meta name="twitter:card" content="summary_large_image">
    <style>{SHARED_VIEWER_CSS}</style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>🥊 Debate Arena</h1>
            <div class="question">{html.escape(share.question)}</div>
            <div class="meta">
                {n_personas} persona{'s' if n_personas != 1 else ''} · {n_rounds} round{'s' if n_rounds != 1 else ''} ·
                {created_str} ·
                share <code>/{share.id}</code>
            </div>
        </div>

        {synth_html}

        <div class="section-label">📜 Full transcript ({len(share.transcript)} turns)</div>
        {turn_html}

        <div class="footer">
            Watch AI personas argue any question.<br>
            <a href="https://github.com/Aryan0707/debate-arena">View the project on GitHub</a>
            · Open source · Free · Runs locally
        </div>
    </div>
</body>
</html>"""


@app.get("/share/{share_id}/json")
def view_share_json(share_id: str) -> JSONResponse:
    """Machine-readable JSON view of a share (for embedding, etc.)."""
    share = get_share(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or expired")
    return JSONResponse({
        "id": share.id,
        "question": share.question,
        "transcript": share.transcript,
        "synthesis": share.synthesis,
        "created_at": share.created_at,
        "config": share.config,
    })


@app.get("/")
def root() -> dict:
    """Health check / root endpoint."""
    return {
        "service": "Debate Arena — Share Viewer",
        "version": "0.1.0",
        "total_shares": len(list_shares()),
        "endpoints": {
            "view_html": "/share/{id}",
            "view_json": "/share/{id}/json",
        },
    }


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


def main() -> None:
    """CLI entry point: `debate-viewer` — launches the share viewer server."""
    import argparse
    import uvicorn

    p = argparse.ArgumentParser(description="Run the debate arena share viewer")
    p.add_argument("--port", type=int, default=8001, help="Port to listen on (default 8001)")
    p.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    p.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev)")
    args = p.parse_args()

    print("🥊 Debate Arena — Share Viewer")
    print(f"   → http://{args.host}:{args.port}")
    print(f"   → Shares will appear at http://{args.host}:{args.port}/share/{{id}}")
    uvicorn.run("debate_arena.viewer:app", host=args.host, port=args.port, reload=args.reload)
