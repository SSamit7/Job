from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import CustomUser
from apps.applications.models import Application
from apps.jobs.models import Job
from .models import Notification
from .services import notify


@receiver(post_save, sender=Job)
def notify_workers_of_new_job(sender, instance, created, **kwargs):
    if not created or instance.status != Job.Status.OPEN:
        return

    # NOTE: this loops every worker on the platform. Fine at this scale;
    # for a larger user base swap this for a filtered/matched subset (e.g.
    # workers whose skills or location match the job) and/or a background
    # task queue instead of doing it inline in the request/signal.
    workers = CustomUser.objects.filter(role=CustomUser.Role.WORKER)
    for worker in workers:
        notify(
            worker,
            f'New job posted: "{instance.title}" - Rs. {instance.budget}',
            kind=Notification.Kind.NEW_JOB,
            link=f"/jobs/{instance.pk}/",
        )


@receiver(post_save, sender=Application)
def notify_client_of_new_application(sender, instance, created, **kwargs):
    if not created:
        return

    notify(
        instance.job.client,
        f'{instance.worker.username} applied to your job "{instance.job.title}"',
        kind=Notification.Kind.NEW_APPLICATION,
        link=f"/jobs/mine/{instance.job.pk}/",
    )
