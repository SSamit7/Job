from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, ClientProfile, WorkerProfile, WorkerAvailability


@receiver(post_save, sender=CustomUser)
def create_role_profile(sender, instance, created, **kwargs):
    """Auto-create the matching profile the moment a user registers."""
    if not created:
        return
    if instance.role == CustomUser.Role.CLIENT:
        ClientProfile.objects.get_or_create(user=instance)
    elif instance.role == CustomUser.Role.WORKER:
        WorkerProfile.objects.get_or_create(user=instance)
        WorkerAvailability.objects.get_or_create(worker=instance)
