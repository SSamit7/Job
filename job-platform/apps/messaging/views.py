from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from apps.contracts.models import Contract
from apps.notifications.models import Notification
from apps.notifications.services import notify
from .forms import MessageForm
from .models import Conversation, Message


def _client_or_worker_q(user):
    return Q(client=user) | Q(worker=user)


@login_required
def conversation_list_view(request):
    contracts = Contract.objects.filter(payment__status="SUCCESS").filter(
        _client_or_worker_q(request.user)
    ).select_related("job", "client", "worker", "payment")

    rows = []
    for contract in contracts:
        conversation = getattr(contract, "conversation", None)
        last_message = conversation.messages.last() if conversation else None
        unread_count = (
            conversation.messages.filter(is_read=False).exclude(sender=request.user).count()
            if conversation
            else 0
        )
        other_party = contract.worker if request.user == contract.client else contract.client
        rows.append(
            {
                "contract": contract,
                "other_party": other_party,
                "last_message": last_message,
                "unread_count": unread_count,
            }
        )

    return render(request, "messaging/conversation_list.html", {"rows": rows})


@login_required
def conversation_detail_view(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk)

    if request.user not in (contract.client, contract.worker):
        django_messages.error(request, "You're not part of this contract.")
        return redirect("messaging:conversation_list")

    if not hasattr(contract, "payment") or contract.payment.status != "SUCCESS":
        django_messages.error(request, "Messaging unlocks once payment for this job is confirmed.")
        return redirect("contracts:contract_detail", pk=contract.pk)

    conversation, _ = Conversation.objects.get_or_create(contract=contract)
    other_party = contract.worker if request.user == contract.client else contract.client

    # Mark anything the other party sent as read now that this user is looking at it.
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()

        notify(
            other_party,
            f"New message from {request.user.username} about \"{contract.job.title}\"",
            kind=Notification.Kind.GENERAL,
            link=f"/messages/{contract.pk}/",
        )
        return redirect("messaging:conversation_detail", contract_pk=contract.pk)

    thread = conversation.messages.select_related("sender")
    return render(
        request,
        "messaging/conversation_detail.html",
        {"contract": contract, "conversation": conversation, "other_party": other_party, "thread": thread, "form": form},
    )
