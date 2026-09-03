"""
One place that actually creates notifications, so every trigger (job
posted, application received, etc.) goes through the same path.

Two channels right now:
- In-app: a Notification row, shown via the bell in the topbar.
- Email: best-effort, using EMAIL_BACKEND from settings. In dev this is the
  console backend, so "sent" emails just print to the runserver terminal -
  swap in real SMTP/SendGrid credentials in production and this starts
  actually landing in inboxes with zero code changes.

True phone notifications (SMS or push) need a separate provider (Twilio for
SMS, Firebase Cloud Messaging for push) and their own API credentials - that
isn't wired in here since no such credentials are available. Email is the
realistic "reaches you outside the app" channel in the meantime.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def notify(recipient, message, kind=Notification.Kind.GENERAL, link=""):
    """Create an in-app notification and best-effort email it."""
    notification = Notification.objects.create(
        recipient=recipient, kind=kind, message=message, link=link
    )

    if recipient.email:
        try:
            full_link = (settings.SITE_BASE_URL + link) if link else settings.SITE_BASE_URL
            send_mail(
                subject="JobPlatform: " + message[:120],
                message=f"{message}\n\nOpen it here: {full_link}",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@jobplatform.local"),
                recipient_list=[recipient.email],
                fail_silently=True,
            )
        except Exception:  # noqa: BLE001 - notifications must never break the request that triggered them
            logger.exception("Failed to email notification to %s", recipient.email)

    return notification
