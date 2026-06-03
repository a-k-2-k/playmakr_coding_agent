"""Pydantic models + in-memory user store."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UserPrefs(BaseModel):
    phone: str = Field(..., description="E.164 phone number, e.g. +15551234567")
    sport: str = Field("basketball", description="Sport key, e.g. basketball")
    league: str = Field("nba", description="League key, e.g. nba")
    teams: List[str] = Field(default_factory=list, description="Team names/abbrevs to follow")


class RegisterRequest(BaseModel):
    phone: str
    sport: str = "basketball"
    league: str = "nba"
    teams: List[str] = Field(default_factory=list)


class InboundSMS(BaseModel):
    """Loose model for Brevo inbound SMS webhook payloads."""
    sender: Optional[str] = None
    text: Optional[str] = None
    # Brevo may use different field names; we normalize in the route.

    class Config:
        extra = "allow"


# ---- In-memory store (swap for Postgres later) ----

class UserStore:
    def __init__(self) -> None:
        self._users: Dict[str, UserPrefs] = {}
        # Track last-seen game state per game id for proactive change detection.
        self._game_state: Dict[str, dict] = {}

    def upsert(self, prefs: UserPrefs) -> UserPrefs:
        self._users[prefs.phone] = prefs
        return prefs

    def get(self, phone: str) -> Optional[UserPrefs]:
        return self._users.get(phone)

    def all(self) -> List[UserPrefs]:
        return list(self._users.values())

    def get_game_state(self, game_id: str) -> Optional[dict]:
        return self._game_state.get(game_id)

    def set_game_state(self, game_id: str, state: dict) -> None:
        self._game_state[game_id] = state


store = UserStore()
