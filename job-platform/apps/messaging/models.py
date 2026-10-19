from django.conf import settings
from django.db import models

from apps.contracts.models import Contract


class Conversation(models.Model):
    """
    One conversation per contract. Deliberately tied to a contract rather
    than being open-ended DMs: it only ever gets created once the contract's
    payment has succeeded, matching the platform's rule that contact details
    (and now messaging) unlock after payment and commission are confirmed -
    not before.
    """

    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name="conversation")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation for {self.contract.job.title}"

    @property
    def client(self):
        return self.contract.client

    @property
    def worker(self):
        return self.contract.worker


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40]}"
