from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _ensure_platform_wallet(sender, **kwargs):
    """
    Guarantee the singleton PlatformWallet row exists the moment migrations
    finish - otherwise it's only lazily created on the first successful
    payment (or the first visit to the in-app wallet page), which means it
    can be genuinely absent from the admin's change list with nothing to
    click into. This makes "Payments > Platform wallet" always show exactly
    one editable row, right from a fresh install.
    """
    from .models import PlatformWallet

    PlatformWallet.get_instance()


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"

    def ready(self):
        import apps.payments.signals  # noqa: F401
        post_migrate.connect(_ensure_platform_wallet, sender=self)
