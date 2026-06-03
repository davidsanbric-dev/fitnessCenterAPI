from __future__ import annotations

import logging
from collections.abc import Sequence

from firebase_admin import messaging

from app.core.firebase_auth import _get_firebase_app

logger = logging.getLogger("uvicorn.error")


def send_push_to_tokens(
    tokens: Sequence[str],
    title: str,
    body: str,
    data: dict | None = None,
) -> list[str]:
    """Best-effort FCM multicast to ``tokens``.

    Returns the subset of tokens that are permanently invalid (unregistered /
    sender-mismatch) so the caller can prune them. Transient failures are not
    returned. Never raises: any error is logged and yields an empty list.
    """
    token_list = [token for token in tokens if token]
    if not token_list:
        return []

    try:
        _get_firebase_app()
        message = messaging.MulticastMessage(
            tokens=token_list,
            notification=messaging.Notification(title=title, body=body),
            # FCM data values must be strings.
            data={key: str(value) for key, value in (data or {}).items()},
            android=messaging.AndroidConfig(priority="high"),
        )
        batch = messaging.send_each_for_multicast(message)
    except Exception:
        logger.warning("FCM push send failed", exc_info=True)
        return []

    invalid: list[str] = []
    for index, response in enumerate(batch.responses):
        if response.success:
            continue
        exception = response.exception
        if isinstance(exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
            invalid.append(token_list[index])
        else:
            logger.warning("FCM delivery error for a token: %s", exception)
    return invalid
