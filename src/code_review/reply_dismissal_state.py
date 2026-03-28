"""Shared state for durable reply-dismissal behavior."""

REPLY_DISMISSAL_ACCEPTED_REPLY_TEXT = (
    "Accepted; this thread will no longer count toward the quality gate."
)


def is_reply_dismissal_accepted_reply(body: str) -> bool:
    """True when *body* is the canonical durable acceptance reply."""
    return (body or "").strip() == REPLY_DISMISSAL_ACCEPTED_REPLY_TEXT
