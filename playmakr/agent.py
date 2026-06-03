"""Agent brain. Single Claude (Haiku) call per inbound message.

The agent acts like a sharp sports analyst: proactive, concise, no filler.
It can request highlights via a lightweight tool the model can call.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from anthropic import Anthropic

from .config import config
from .highlights import find_highlights, format_highlights_sms
from .models import UserPrefs

logger = logging.getLogger("playmakr.agent")

SYSTEM_PROMPT = (
    "You are Playmakr, a knowledgeable, proactive sports analyst delivered over SMS. "
    "Be concise and high-signal: scores, momentum, standouts, what matters next. "
    "No filler, no greetings, no 'as an AI'. Keep replies under 320 characters when possible. "
    "If the user asks for highlights, clips, reels, or a recap of a player/team/game, "
    "call the get_highlights tool with a short query like 'LeBron James most recent game'. "
    "Use any provided live game context to ground your answer."
)

HIGHLIGHTS_TOOL = {
    "name": "get_highlights",
    "description": "Find short highlight video clips for a player, team, or game.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural phrase, e.g. 'LeBron James most recent game' or 'Celtics vs Heat'.",
            }
        },
        "required": ["query"],
    },
}

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _build_context(user_prefs: Optional[UserPrefs], recent_game_context: Optional[str]) -> str:
    parts = []
    if user_prefs:
        teams = ", ".join(user_prefs.teams) if user_prefs.teams else "none set"
        parts.append(f"User follows {user_prefs.league.upper()} | teams: {teams}.")
    if recent_game_context:
        parts.append(f"Live context: {recent_game_context}")
    return "\n".join(parts)


def respond(
    user_prefs: Optional[UserPrefs],
    inbound_message: str,
    recent_game_context: Optional[str] = None,
) -> str:
    """Return the agent's SMS reply string for an inbound message."""
    if not config.ANTHROPIC_API_KEY:
        # Degrade gracefully so the skeleton runs without keys.
        return _fallback(inbound_message)

    client = _get_client()
    context = _build_context(user_prefs, recent_game_context)
    user_content = inbound_message if not context else f"{context}\n\nUser: {inbound_message}"

    try:
        msg = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            tools=[HIGHLIGHTS_TOOL],
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Claude call failed: %s", e)
        return _fallback(inbound_message)

    # Handle a single tool call (highlights) then do a follow-up turn.
    tool_use = next((b for b in msg.content if b.type == "tool_use"), None)
    if tool_use and tool_use.name == "get_highlights":
        query = tool_use.input.get("query", inbound_message)
        clips = find_highlights(query)
        # Short-circuit: SMS-friendly highlights reply is good enough for v1.
        return format_highlights_sms(query, clips)

    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    return text or _fallback(inbound_message)


def _fallback(inbound_message: str) -> str:
    lower = inbound_message.lower()
    if any(k in lower for k in ("highlight", "clip", "reel", "recap")):
        clips = find_highlights(inbound_message)
        return format_highlights_sms(inbound_message, clips)
    return "Playmakr is live. Ask for scores, recaps, or highlights of your team."
