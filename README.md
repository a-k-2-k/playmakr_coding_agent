# Playmakr — Agent Core + SMS Activation

A proactive sports AI agent that delivers personalized game updates over SMS.

Text Playmakr a question (e.g. *"show me LeBron's highlights from his most
recent game"*) and get a concise, analyst-grade reply with real clips. Playmakr
also reaches out **first** when something notable happens in a game you follow.

## Stack
- **FastAPI** backend
- **Brevo (Sendinblue)** transactional SMS
- **Anthropic Claude Haiku** agent brain (one call per message)
- **APScheduler** proactive alerts (every 5 min)
- **ESPN** unofficial scoreboard for live data
- In-memory user store (Postgres later)

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r playmakr/requirements.txt
cp playmakr/.env.example .env   # fill in keys
uvicorn playmakr.main:app --reload
```

Runs fine with **no keys** for local testing: the agent falls back to
search-link highlights and SMS sends are logged instead of charged.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/users/register` | Register phone + sport/team prefs |
| POST | `/webhook/sms` | Brevo inbound SMS -> agent -> outbound reply |
| GET  | `/scores?sport=basketball&league=nba` | Live ESPN scores |
| GET  | `/highlights?q=...` | Test the clip finder directly |
| GET  | `/health` | Liveness |

### Examples
```bash
curl -X POST localhost:8000/users/register -H 'content-type: application/json' \
  -d '{"phone":"+15551234567","league":"nba","teams":["Lakers"]}'

curl "localhost:8000/highlights?q=LeBron+James+most+recent+game"

curl -X POST localhost:8000/webhook/sms -H 'content-type: application/json' \
  -d '{"sender":"+15551234567","text":"show me LeBron highlights from his last game"}'
```

## Highlights feature
`playmakr/highlights.py` finds short clips for any recap/highlight query:
1. If `TWITTER_BEARER_TOKEN` is set, searches X/Twitter recent posts with native
   video from known highlight accounts (NBA, Ballislife, BleacherReport, ...).
2. Always falls back to tappable X video search + YouTube deep links so users
   get something watchable even with no keys.

The agent (`agent.py`) exposes this to Claude as a `get_highlights` tool, so the
model decides when to fetch clips.

## Proactive alerts
`scheduler.py` scans live games for each user's followed teams every 5 min and
texts them on: **FINAL**, **OT started**, or a **big score swing**.

## Roadmap (per product plan)
- iMessage / email / WhatsApp / Telegram / Discord channels
- Stripe links for group-chat subscriptions
- Auto-clipped reels/TikToks on recap queries (native video extraction)
- Real-time + historical + comparison queries
- Postgres, auth — later

## Not included yet (intentionally)
Auth/JWT, Stripe, database. Single Claude call per message. Keep it lean.
