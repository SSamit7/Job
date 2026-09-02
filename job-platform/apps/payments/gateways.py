"""
Real integrations with eSewa (ePay v2) and Khalti (KPG-2 / ePayment).
Built against the official specs at developer.esewa.com.np and
docs.khalti.com. Both gateways redirect the user's own browser to their
hosted checkout page, then redirect back to a callback URL here - neither
step requires this server to be reachable from the internet during local
development, since it's the user's browser doing the redirecting.

eSewa ships a genuinely public sandbox (EPAYTEST / the secret key below),
so it works out of the box. Khalti has no such universal key - each
developer needs their own free sandbox account at test-admin.khalti.com.
"""
import base64
import hashlib
import hmac
import json

import requests
from django.conf import settings


class KhaltiError(Exception):
    """Raised when Khalti's API rejects or fails a request."""


class KhaltiNotConfigured(KhaltiError):
    """Raised when KHALTI_SECRET_KEY hasn't been set."""


# --------------------------------------------------------------------------
# eSewa
# --------------------------------------------------------------------------

def _esewa_signature(fields: dict, signed_field_names: list) -> str:
    """HMAC-SHA256, base64-encoded, over 'name=value,name=value,...' in the given order."""
    message = ",".join(f"{name}={fields.get(name, '')}" for name in signed_field_names)
    digest = hmac.new(
        settings.ESEWA_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def esewa_payment_fields(amount, transaction_uuid, success_url, failure_url):
    """Build the signed hidden-field set for the auto-submitting eSewa form."""
    amount_str = str(amount)  # Decimal -> "500.00", matches what we sign

    signed_field_names = ["total_amount", "transaction_uuid", "product_code"]
    fields = {
        "amount": amount_str,
        "tax_amount": "0",
        "total_amount": amount_str,
        "transaction_uuid": transaction_uuid,
        "product_code": settings.ESEWA_MERCHANT_CODE,
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "success_url": success_url,
        "failure_url": failure_url,
        "signed_field_names": ",".join(signed_field_names),
    }
    fields["signature"] = _esewa_signature(fields, signed_field_names)
    return fields


def esewa_decode_callback(data_param: str) -> dict:
    """Decode the base64 `data` query param eSewa redirects back with."""
    decoded = base64.b64decode(data_param).decode("utf-8")
    return json.loads(decoded)


def esewa_verify_callback(payload: dict) -> bool:
    """Recompute the signature over exactly the fields eSewa says it signed, and compare."""
    signed_field_names = payload.get("signed_field_names", "")
    field_list = [f.strip() for f in signed_field_names.split(",") if f.strip()]
    if not field_list:
        return False
    expected = _esewa_signature(payload, field_list)
    return hmac.compare_digest(expected, payload.get("signature", ""))


def esewa_check_status(transaction_uuid, total_amount):
    """
    Defense in depth: ask eSewa directly rather than trusting the browser
    redirect alone (a redirect can be replayed or forged; this can't).
    """
    try:
        response = requests.get(
            settings.ESEWA_STATUS_CHECK_URL,
            params={
                "product_code": settings.ESEWA_MERCHANT_CODE,
                "total_amount": str(total_amount),
                "transaction_uuid": transaction_uuid,
            },
            timeout=8,
        )
        return response.json()
    except (requests.RequestException, ValueError):
        return {"status": "UNKNOWN"}


# --------------------------------------------------------------------------
# Khalti
# --------------------------------------------------------------------------

def khalti_initiate(amount, purchase_order_id, purchase_order_name, customer, return_url):
    """
    Server-side call that starts a Khalti payment. `customer` is a dict with
    name/email/phone. Returns (pidx, payment_url) on success - the caller
    should redirect the user's browser to payment_url.
    """
    if not settings.KHALTI_SECRET_KEY:
        raise KhaltiNotConfigured(
            "Khalti isn't set up yet. Sign up for a free sandbox merchant account at "
            "https://test-admin.khalti.com, then add the secret key as KHALTI_SECRET_KEY in .env."
        )

    payload = {
        "return_url": return_url,
        "website_url": settings.SITE_BASE_URL,
        "amount": int(amount * 100),  # Khalti wants paisa, not rupees
        "purchase_order_id": purchase_order_id,
        "purchase_order_name": purchase_order_name,
        "customer_info": {
            "name": customer.get("name") or "JobPlatform User",
            "email": customer.get("email") or "user@example.com",
            "phone": customer.get("phone") or "9800000000",
        },
    }
    try:
        response = requests.post(
            settings.KHALTI_INITIATE_URL,
            json=payload,
            headers={"Authorization": f"key {settings.KHALTI_SECRET_KEY}", "Content-Type": "application/json"},
            timeout=10,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise KhaltiError(f"Couldn't reach Khalti: {exc}") from exc

    if response.status_code != 200 or "pidx" not in data:
        raise KhaltiError(data)

    return data["pidx"], data["payment_url"]


def khalti_lookup(pidx):
    """Authoritative status check - Khalti's own docs say to always do this after the redirect."""
    response = requests.post(
        settings.KHALTI_LOOKUP_URL,
        json={"pidx": pidx},
        headers={"Authorization": f"key {settings.KHALTI_SECRET_KEY}", "Content-Type": "application/json"},
        timeout=10,
    )
    return response.json()
