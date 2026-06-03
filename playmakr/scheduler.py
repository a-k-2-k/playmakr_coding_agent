"""APScheduler proactive alerts.

Every N minutes: scan live games for any registered user's followed teams,
and fire a proactive SMS when something notable changes:
  - game went final
  - overtime started
  - a meaningful score swing since last check
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import config
from .models import store
from .sms import send_sms
from .sports import find_games_for_team

logger = logging.getLogger("playmakr.scheduler")

SWING_THRESHOLD = 8  # points of margin change to count as a "swing"

scheduler = BackgroundScheduler()


def _margin(game: dict) -> int:
    try:
        return int(game.get("home_score") or 0) - int(game.get("away_score") or 0)
    except (TypeError, ValueError):
        return 0


def _alert_text(game: dict, reason: str) -> str:
    h = next((t for t in game["teams"] if t["home"]), {})
    a = next((t for t in game["teams"] if not t["home"]), {})
    score = f"{a.get('abbrev')} {a.get('score')} - {h.get('abbrev')} {h.get('score')}"
    detail = game.get("status_detail") or ""
    return f"{reason}: {score} ({detail})".strip()


def check_games() -> None:
    """Core scheduled job. Diff current game state vs last seen and alert."""
    users = store.all()
    if not users:
        return

    for user in users:
        teams = user.teams or []
        for team in teams:
            for game in find_games_for_team(team, user.sport, user.league):
                gid = game["id"]
                prev = store.get_game_state(gid)
                reason = None

                if prev is None:
                    # First time we see it; record baseline, no alert.
                    store.set_game_state(gid, game)
                    continue

                # Final
                if game.get("completed") and not prev.get("completed"):
                    reason = "FINAL"
                # Overtime start
                elif (game.get("period") or 0) > 4 and (prev.get("period") or 0) <= 4:
                    reason = "OT STARTED"
                # Score swing
                elif abs(_margin(game) - _margin(prev)) >= SWING_THRESHOLD:
                    reason = "Big swing"

                store.set_game_state(gid, game)
                if reason:
                    body = _alert_text(game, reason)
                    logger.info("Proactive alert to %s: %s", user.phone, body)
                    send_sms(user.phone, body)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        check_games,
        "interval",
        minutes=config.SCHEDULER_INTERVAL_MIN,
        id="check_games",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started (every %s min).", config.SCHEDULER_INTERVAL_MIN)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
