from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Notification


@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(recipient=request.user)
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def open_notification_view(request, pk):
    """Marks a notification read, then sends the user on to whatever it's about."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    if notification.link:
        return redirect(notification.link)
    return redirect("notifications:list")


@login_required
def mark_all_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
