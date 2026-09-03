"""
A payment callback shouldn't depend on the user's browser session still
being alive when the gateway redirects back - a slow OTP entry at eSewa/
Khalti can outlast a session timeout. So every outgoing payment/top-up
carries a signed token identifying exactly which row and which user it
belongs to. It's tamper-proof (signed with SECRET_KEY) and short-lived, so
even if a callback URL leaked, it's useless after it expires.
"""
from django.core import signing

_SALT = "payments.callback"
_MAX_AGE_SECONDS = 60 * 60  # 1 hour - generous for a slow checkout, short enough to limit exposure if a URL leaks


def make_callback_token(kind: str, obj_id: int, user_id: int) -> str:
    return signing.dumps({"kind": kind, "id": obj_id, "user_id": user_id}, salt=_SALT)


def read_callback_token(token: str, expected_kind: str):
    """Returns the decoded dict, or None if missing/invalid/expired/wrong kind."""
    if not token:
        return None
    try:
        data = signing.loads(token, salt=_SALT, max_age=_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return None
    if data.get("kind") != expected_kind:
        return None
    return data
