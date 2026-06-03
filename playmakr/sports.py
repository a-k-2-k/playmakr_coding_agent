"""Sports data fetcher. Real ESPN scoreboard + recap stubs."""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

logger = logging.getLogger("playmakr.sports")

# ESPN unofficial site API. sport/league are path segments,
# e.g. basketball/nba, football/nfl, baseball/mlb, hockey/nhl.
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"


def get_live_scores(sport: str = "basketball", league: str = "nba") -> List[dict]:
    """Return a normalized list of games from ESPN's scoreboard.

    Each game dict: id, name, short_name, state, status_detail, period,
    clock, teams [{abbrev, name, score, home}], home_score, away_score.
    """
    url = ESPN_SCOREBOARD.format(sport=sport, league=league)
    try:
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.error("ESPN scoreboard fetch failed: %s", e)
        return []

    games: List[dict] = []
    for event in data.get("events", []):
        comp = (event.get("competitions") or [{}])[0]
        status = event.get("status", {})
        stype = status.get("type", {})
        competitors = comp.get("competitors", [])

        teams = []
        home_score = away_score = None
        for c in competitors:
            t = c.get("team", {})
            score = c.get("score")
            is_home = c.get("homeAway") == "home"
            teams.append({
                "abbrev": t.get("abbreviation"),
                "name": t.get("displayName"),
                "score": score,
                "home": is_home,
            })
            if is_home:
                home_score = score
            else:
                away_score = score

        games.append({
            "id": event.get("id"),
            "name": event.get("name"),
            "short_name": event.get("shortName"),
            "state": stype.get("state"),          # pre | in | post
            "completed": stype.get("completed", False),
            "status_detail": stype.get("detail"),
            "status_name": stype.get("name"),     # e.g. STATUS_END_PERIOD, STATUS_FINAL
            "period": status.get("period"),
            "clock": status.get("displayClock"),
            "teams": teams,
            "home_score": home_score,
            "away_score": away_score,
        })
    return games


def find_games_for_team(team: str, sport: str = "basketball", league: str = "nba") -> List[dict]:
    """Filter live scores to games involving `team` (matches abbrev or name, case-insensitive)."""
    if not team:
        return []
    needle = team.lower()
    out = []
    for g in get_live_scores(sport, league):
        for t in g["teams"]:
            if needle in (t.get("abbrev") or "").lower() or needle in (t.get("name") or "").lower():
                out.append(g)
                break
    return out


def get_game_recap(game_id: str, sport: str = "basketball", league: str = "nba") -> Optional[dict]:
    """Stub recap. Returns a summary dict for a given game id.

    TODO: wire ESPN summary endpoint:
    site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={id}
    """
    return {
        "game_id": game_id,
        "recap": f"Recap for game {game_id} not yet wired. (stub)",
        "top_performers": [],
    }
