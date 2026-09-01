from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import CustomUser
from .models import WorkerWallet


@receiver(post_save, sender=CustomUser)
def create_worker_wallet(sender, instance, created, **kwargs):
    if created and instance.role == CustomUser.Role.WORKER:
        WorkerWallet.objects.get_or_create(worker=instance)
