"""
Catches the single most likely way this app quietly "doesn't work with real
money": DEBUG=False (production) but the payment settings are still pointed
at eSewa's sandbox, or Khalti isn't configured at all. Runs automatically on
every `manage.py check`, `runserver`, and `migrate` - shows up loudly in the
terminal instead of silently taking fake payments in production.
"""
from django.conf import settings
from django.core.checks import Warning, register


@register()
def payment_gateway_production_check(app_configs, **kwargs):
    issues = []

    if settings.DEBUG:
        return issues  # sandbox credentials are expected and fine in dev

    if settings.ESEWA_MERCHANT_CODE == "EPAYTEST":
        issues.append(
            Warning(
                "DEBUG=False but ESEWA_MERCHANT_CODE is still eSewa's public sandbox value 'EPAYTEST'. "
                "Real eSewa payments will not work until you set your own merchant code and secret key "
                "(from the eSewa Merchant Dashboard, after completing eSewa's merchant KYC) in .env.",
                id="payments.W001",
            )
        )

    if "rc-epay.esewa.com.np" in settings.ESEWA_PAYMENT_URL or "uat.esewa.com.np" in settings.ESEWA_STATUS_CHECK_URL:
        issues.append(
            Warning(
                "DEBUG=False but ESEWA_PAYMENT_URL / ESEWA_STATUS_CHECK_URL still point at eSewa's UAT/sandbox "
                "hosts (rc-epay.esewa.com.np / uat.esewa.com.np). Set them to the production hosts "
                "(epay.esewa.com.np) in .env once you have real merchant credentials.",
                id="payments.W002",
            )
        )

    if not settings.KHALTI_SECRET_KEY:
        issues.append(
            Warning(
                "DEBUG=False but KHALTI_SECRET_KEY is empty. Khalti payments will show a 'not configured' "
                "error to users until you sign up for a Khalti merchant account and set this in .env.",
                id="payments.W003",
            )
        )

    if "127.0.0.1" in settings.SITE_BASE_URL or "localhost" in settings.SITE_BASE_URL:
        issues.append(
            Warning(
                "DEBUG=False but SITE_BASE_URL is still localhost. eSewa/Khalti redirect users' browsers back "
                "to this URL after payment - it needs to be your real public domain (with HTTPS) in production.",
                id="payments.W004",
            )
        )

    return issues
