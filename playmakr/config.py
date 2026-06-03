"""Environment configuration for Playmakr."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Anthropic (agent brain)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-latest")

    # Brevo (SMS)
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_NUMBER: str = os.getenv("BREVO_SENDER_NUMBER", "Playmakr")

    # Scheduler
    SCHEDULER_INTERVAL_MIN: int = int(os.getenv("SCHEDULER_INTERVAL_MIN", "5"))

    # Highlights (X/Twitter scraping)
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")
    # Comma-separated X/Twitter handles to source clips from. Empty = no
    # account filter (search all of X). Configure per-deployment, not in code.
    HIGHLIGHT_ACCOUNTS: list[str] = [
        h.strip() for h in os.getenv("HIGHLIGHT_ACCOUNTS", "").split(",") if h.strip()
    ]

    @classmethod
    def require(cls, *names: str) -> None:
        """Raise if any of the named config values is empty."""
        missing = [n for n in names if not getattr(cls, n, "")]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


config = Config()
