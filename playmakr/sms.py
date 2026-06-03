"""Brevo (Sendinblue) transactional SMS wrapper."""
from __future__ import annotations

import logging

import httpx

from .config import config

logger = logging.getLogger("playmakr.sms")

BREVO_SMS_URL = "https://api.brevo.com/v3/transactionalSMS/sms"


def send_sms(to: str, message: str) -> dict:
    """Send an SMS via Brevo. Returns the API response dict.

    No "sent from" boilerplate is added to the message body.
    """
    if not config.BREVO_API_KEY:
        logger.warning("BREVO_API_KEY not set; SMS to %s not sent. Body: %s", to, message)
        return {"skipped": True, "reason": "no_api_key"}

    payload = {
        "type": "transactional",
        "sender": config.BREVO_SENDER_NUMBER,
        "recipient": to,
        "content": message,
    }
    headers = {
        "api-key": config.BREVO_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        resp = httpx.post(BREVO_SMS_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Brevo SMS error %s: %s", e.response.status_code, e.response.text)
        return {"error": e.response.text, "status": e.response.status_code}
    except Exception as e:  # noqa: BLE001
        logger.error("Brevo SMS failed: %s", e)
        return {"error": str(e)}
