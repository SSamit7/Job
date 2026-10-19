from django.db.models import Q

from .models import Message


def unread_messages(request):
    if not request.user.is_authenticated:
        return {"unread_messages_count": 0}

    count = (
        Message.objects.filter(
            Q(conversation__contract__client=request.user) | Q(conversation__contract__worker=request.user)
        )
        .filter(is_read=False)
        .exclude(sender=request.user)
        .count()
    )
    return {"unread_messages_count": count}
