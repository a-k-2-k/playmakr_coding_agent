"""Playmakr FastAPI app + routes."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from . import agent
from .highlights import find_highlights, format_highlights_sms
from .models import RegisterRequest, UserPrefs, store
from .scheduler import start_scheduler, stop_scheduler
from .sms import send_sms
from .sports import find_games_for_team, get_live_scores

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("playmakr")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Playmakr", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "users": len(store.all())}


@app.post("/users/register")
def register(req: RegisterRequest) -> dict:
    prefs = store.upsert(UserPrefs(**req.model_dump()))
    return {"registered": True, "user": prefs.model_dump()}


def _normalize_inbound(payload: dict) -> tuple[str, str]:
    """Extract (sender, text) from a Brevo inbound SMS payload.

    Brevo inbound webhook fields vary; we check the common keys.
    """
    sender = (
        payload.get("sender")
        or payload.get("from")
        or payload.get("msisdn")
        or ""
    )
    text = (
        payload.get("text")
        or payload.get("message")
        or payload.get("content")
        or ""
    )
    return str(sender), str(text)


@app.post("/webhook/sms")
async def inbound_sms(request: Request) -> dict:
    payload = await request.json()
    sender, text = _normalize_inbound(payload)
    if not sender or not text:
        return {"error": "missing sender or text", "received": payload}

    prefs = store.get(sender)

    # Build optional live context from the user's followed teams.
    context = None
    if prefs and prefs.teams:
        ctx_games = []
        for team in prefs.teams:
            for g in find_games_for_team(team, prefs.sport, prefs.league):
                ctx_games.append(f"{g['short_name']} {g.get('status_detail','')}".strip())
        if ctx_games:
            context = "; ".join(ctx_games[:3])

    reply = agent.respond(prefs, text, recent_game_context=context)
    send_result = send_sms(sender, reply)
    return {"reply": reply, "send_result": send_result}


@app.get("/scores")
def scores(sport: str = "basketball", league: str = "nba") -> dict:
    return {"games": get_live_scores(sport, league)}


@app.get("/highlights")
def highlights(q: str) -> dict:
    """Quick test endpoint: GET /highlights?q=LeBron+James+most+recent+game"""
    clips = find_highlights(q)
    return {"query": q, "clips": clips, "sms": format_highlights_sms(q, clips)}
