"""
Communication System Views
============================
Chat (1-to-1 + Group) · Inbox · Notifications — all AJAX-ready.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Max, OuterRef, Subquery, Count, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.defaultfilters import truncatewords

from accounts.models import User
from classes.models import Group
from .models import (
    ChatConversation, ChatMessage,
    GroupChatMessage,
    InboxThread, InboxMessage,
    SmartNotification,
)
from .permissions import get_allowed_contacts, can_message, can_access_group_chat


# ─────────────────────────────────────────────────────────
#  CHAT — Main Page
# ─────────────────────────────────────────────────────────

@login_required
def chat_home(request):
    """Render the full chat page (sidebar + message panel)."""
    user = request.user
    contacts = get_allowed_contacts(user).select_related('teacher', 'student')

    # Conversations this user participates in
    convos = (
        ChatConversation.objects
        .filter(Q(participant1=user) | Q(participant2=user))
        .select_related('participant1', 'participant2')
        .order_by('-updated_at')
    )

    # Annotate with last message preview & unread count
    conversation_list = []
    for c in convos:
        other = c.other_user(user)
        last_msg = c.messages.order_by('-created_at').first()
        unread = c.messages.filter(status__in=['sent', 'delivered']).exclude(sender=user).count()
        conversation_list.append({
            'id': c.id,
            'other_user': other,
            'last_message': last_msg,
            'unread_count': unread,
            'updated_at': c.updated_at,
        })

    # Group chats the user can access
    if user.role == 'admin':
        groups = Group.objects.all().select_related('class_assigned')
    elif user.role == 'formateur':
        try:
            groups = Group.objects.filter(teachers=user.teacher).select_related('class_assigned')
        except Exception:
            groups = Group.objects.none()
    elif user.role == 'stagiaire':
        try:
            groups = Group.objects.filter(students=user.student).select_related('class_assigned')
        except Exception:
            groups = Group.objects.none()
    else:
        groups = Group.objects.none()

    # Annotate group unread (messages not by me, created after last time I viewed — simplified: count all not by me in last 24h)
    group_list = []
    for g in groups:
        last_grp_msg = g.chat_messages.order_by('-created_at').first()
        group_list.append({
            'group': g,
            'last_message': last_grp_msg,
        })

    context = {
        'conversation_list': conversation_list,
        'group_list': group_list,
        'contacts': contacts,
    }
    return render(request, 'school_communication/chat.html', context)


# ─────────────────────────────────────────────────────────
#  CHAT — AJAX Endpoints
# ─────────────────────────────────────────────────────────

@login_required
@require_GET
def chat_messages_api(request, conversation_id):
    """Return messages for a 1-to-1 conversation (JSON)."""
    user = request.user
    convo = get_object_or_404(ChatConversation, pk=conversation_id)

    # Security: user must be a participant
    if user != convo.participant1 and user != convo.participant2:
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Mark messages as seen
    convo.messages.exclude(sender=user).filter(status__in=['sent', 'delivered']).update(status='seen')

    page = int(request.GET.get('page', 1))
    messages_qs = convo.messages.select_related('sender').order_by('-created_at')
    paginator = Paginator(messages_qs, 50)
    page_obj = paginator.get_page(page)

    messages_data = []
    for m in reversed(page_obj.object_list):
        messages_data.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.get_full_name() or m.sender.username,
            'body': m.body,
            'attachment': m.attachment.url if m.attachment else None,
            'attachment_name': m.attachment_name,
            'is_image': m.is_image,
            'status': m.status,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_mine': m.sender_id == user.pk,
        })

    other = convo.other_user(user)
    return JsonResponse({
        'messages': messages_data,
        'has_previous': page_obj.has_previous(),
        'other_user': {
            'id': other.pk,
            'name': other.get_full_name() or other.username,
            'role': other.role,
        },
    })


@login_required
@require_POST
def chat_send_api(request, conversation_id):
    """Send a message in a 1-to-1 conversation."""
    user = request.user
    convo = get_object_or_404(ChatConversation, pk=conversation_id)

    if user != convo.participant1 and user != convo.participant2:
        return JsonResponse({'error': 'Access denied'}, status=403)

    body = request.POST.get('body', '').strip()
    attachment = request.FILES.get('attachment')

    if not body and not attachment:
        return JsonResponse({'error': 'Empty message'}, status=400)

    msg = ChatMessage.objects.create(
        conversation=convo,
        sender=user,
        body=body,
        attachment=attachment,
        attachment_name=attachment.name if attachment else '',
    )
    convo.updated_at = timezone.now()
    convo.save(update_fields=['updated_at'])

    # Create notification for recipient
    other = convo.other_user(user)
    SmartNotification.objects.create(
        recipient=other,
        notif_type='info',
        category='chat',
        title=f'New message from {user.get_full_name() or user.username}',
        message=truncatewords(body, 12) if body else 'Sent an attachment',
        url=f'/communication/chat/?open={convo.pk}',
    )

    return JsonResponse({
        'id': msg.id,
        'sender_id': msg.sender_id,
        'sender_name': user.get_full_name() or user.username,
        'body': msg.body,
        'attachment': msg.attachment.url if msg.attachment else None,
        'attachment_name': msg.attachment_name,
        'is_image': msg.is_image,
        'status': msg.status,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
        'is_mine': True,
    })


@login_required
@require_POST
def chat_start_api(request):
    """Start a new 1-to-1 conversation (or return existing one)."""
    user = request.user
    other_id = request.POST.get('user_id')
    if not other_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    other = get_object_or_404(User, pk=other_id)
    if not can_message(user, other):
        return JsonResponse({'error': 'You are not allowed to message this user.'}, status=403)

    # Normalise order so participant1.pk < participant2.pk for uniqueness
    p1, p2 = (user, other) if user.pk < other.pk else (other, user)
    convo, created = ChatConversation.objects.get_or_create(
        participant1=p1, participant2=p2,
    )
    return JsonResponse({'conversation_id': convo.pk, 'created': created})


# ─────────────────────────────────────────────────────────
#  GROUP CHAT — AJAX
# ─────────────────────────────────────────────────────────

@login_required
@require_GET
def group_chat_messages_api(request, group_id):
    """Return messages for a group chat (JSON)."""
    user = request.user
    group = get_object_or_404(Group, pk=group_id)

    if not can_access_group_chat(user, group):
        return JsonResponse({'error': 'Access denied'}, status=403)

    page = int(request.GET.get('page', 1))
    messages_qs = group.chat_messages.select_related('sender').order_by('-created_at')
    paginator = Paginator(messages_qs, 50)
    page_obj = paginator.get_page(page)

    messages_data = []
    for m in reversed(page_obj.object_list):
        messages_data.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.get_full_name() or m.sender.username,
            'body': m.body,
            'attachment': m.attachment.url if m.attachment else None,
            'attachment_name': m.attachment_name,
            'is_image': m.is_image,
            'status': m.status,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_mine': m.sender_id == user.pk,
        })

    return JsonResponse({
        'messages': messages_data,
        'has_previous': page_obj.has_previous(),
        'group': {
            'id': group.pk,
            'name': str(group),
        },
    })


@login_required
@require_POST
def group_chat_send_api(request, group_id):
    """Send a message in a group chat."""
    user = request.user
    group = get_object_or_404(Group, pk=group_id)

    if not can_access_group_chat(user, group):
        return JsonResponse({'error': 'Access denied'}, status=403)

    body = request.POST.get('body', '').strip()
    attachment = request.FILES.get('attachment')

    if not body and not attachment:
        return JsonResponse({'error': 'Empty message'}, status=400)

    msg = GroupChatMessage.objects.create(
        group=group,
        sender=user,
        body=body,
        attachment=attachment,
        attachment_name=attachment.name if attachment else '',
    )

    return JsonResponse({
        'id': msg.id,
        'sender_id': msg.sender_id,
        'sender_name': user.get_full_name() or user.username,
        'body': msg.body,
        'attachment': msg.attachment.url if msg.attachment else None,
        'attachment_name': msg.attachment_name,
        'is_image': msg.is_image,
        'status': msg.status,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
        'is_mine': True,
    })


# ─────────────────────────────────────────────────────────
#  INBOX — Pages
# ─────────────────────────────────────────────────────────

@login_required
def inbox_home(request):
    """Inbox main page — folders + message list."""
    user = request.user
    folder = request.GET.get('folder', 'inbox')
    contacts = get_allowed_contacts(user).select_related('teacher', 'student')

    if folder == 'inbox':
        messages_qs = (
            InboxMessage.objects
            .filter(receiver=user, is_archived_by_receiver=False)
            .select_related('sender', 'thread')
        )
    elif folder == 'sent':
        messages_qs = (
            InboxMessage.objects
            .filter(sender=user, is_archived_by_sender=False)
            .select_related('receiver', 'thread')
        )
    elif folder == 'archived':
        messages_qs = (
            InboxMessage.objects
            .filter(
                Q(receiver=user, is_archived_by_receiver=True) |
                Q(sender=user, is_archived_by_sender=True)
            )
            .select_related('sender', 'receiver', 'thread')
        )
    else:
        messages_qs = InboxMessage.objects.none()

    # Group by thread — show only the latest message per thread
    thread_ids = messages_qs.values_list('thread_id', flat=True).distinct()
    threads = []
    for tid in thread_ids:
        latest_msg = messages_qs.filter(thread_id=tid).order_by('-created_at').first()
        if latest_msg:
            threads.append(latest_msg)

    # Sort by date
    threads.sort(key=lambda m: m.created_at, reverse=True)

    paginator = Paginator(threads, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    # Unread count for badge
    unread_count = InboxMessage.objects.filter(
        receiver=user, is_read=False, is_archived_by_receiver=False
    ).count()

    context = {
        'folder': folder,
        'threads': page_obj,
        'unread_count': unread_count,
        'contacts': contacts,
    }
    return render(request, 'school_communication/inbox.html', context)


@login_required
def inbox_thread_detail(request, thread_id):
    """View all messages in a thread."""
    user = request.user
    thread = get_object_or_404(InboxThread, pk=thread_id)

    # Security: user must be sender or receiver of at least one message in this thread
    if not thread.messages.filter(Q(sender=user) | Q(receiver=user)).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Mark as read
    thread.messages.filter(receiver=user, is_read=False).update(is_read=True)

    messages_list = thread.messages.select_related('sender', 'receiver').order_by('created_at')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = []
        for m in messages_list:
            data.append({
                'id': m.id,
                'sender_id': m.sender_id,
                'sender_name': m.sender.get_full_name() or m.sender.username,
                'receiver_name': m.receiver.get_full_name() or m.receiver.username,
                'body': m.body,
                'attachment': m.attachment.url if m.attachment else None,
                'attachment_name': m.attachment_name,
                'priority': m.priority,
                'is_read': m.is_read,
                'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_mine': m.sender_id == user.pk,
            })
        return JsonResponse({
            'thread_id': thread.pk,
            'subject': thread.subject,
            'messages': data,
        })

    context = {
        'thread': thread,
        'messages_list': messages_list,
    }
    return render(request, 'school_communication/inbox_thread.html', context)


@login_required
@require_POST
def inbox_compose(request):
    """Compose a new inbox message (new thread)."""
    user = request.user
    receiver_id = request.POST.get('receiver_id')
    subject = request.POST.get('subject', '').strip()
    body = request.POST.get('body', '').strip()
    priority = request.POST.get('priority', 'medium')
    attachment = request.FILES.get('attachment')

    if not receiver_id or not subject or not body:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'All fields are required.'}, status=400)
        from django.contrib import messages as django_messages
        django_messages.error(request, 'Receiver, subject, and body are required.')
        return redirect('school_communication:inbox_home')

    receiver = get_object_or_404(User, pk=receiver_id)
    if not can_message(user, receiver):
        return JsonResponse({'error': 'You are not allowed to message this user.'}, status=403)

    thread = InboxThread.objects.create(subject=subject)
    msg = InboxMessage.objects.create(
        thread=thread,
        sender=user,
        receiver=receiver,
        body=body,
        priority=priority,
        attachment=attachment,
        attachment_name=attachment.name if attachment else '',
    )

    # Notification
    SmartNotification.objects.create(
        recipient=receiver,
        notif_type='warning' if priority == 'high' else 'info',
        category='inbox',
        title=f'New message: {subject}',
        message=truncatewords(body, 12),
        url=f'/communication/inbox/thread/{thread.pk}/',
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'thread_id': thread.pk})

    from django.contrib import messages as django_messages
    django_messages.success(request, 'Message sent successfully!')
    return redirect('school_communication:inbox_home')


@login_required
@require_POST
def inbox_reply(request, thread_id):
    """Reply to an existing thread."""
    user = request.user
    thread = get_object_or_404(InboxThread, pk=thread_id)

    # Find who to reply to (the other participant)
    last_msg = thread.messages.exclude(sender=user).order_by('-created_at').first()
    if not last_msg:
        last_msg = thread.messages.order_by('-created_at').first()

    if not last_msg:
        return JsonResponse({'error': 'Thread is empty.'}, status=400)

    # The receiver of the reply is the person who is NOT me
    if last_msg.sender == user:
        receiver = last_msg.receiver
    else:
        receiver = last_msg.sender

    if not can_message(user, receiver):
        return JsonResponse({'error': 'You are not allowed to message this user.'}, status=403)

    body = request.POST.get('body', '').strip()
    priority = request.POST.get('priority', 'medium')
    attachment = request.FILES.get('attachment')

    if not body:
        return JsonResponse({'error': 'Reply body is required.'}, status=400)

    msg = InboxMessage.objects.create(
        thread=thread,
        sender=user,
        receiver=receiver,
        body=body,
        priority=priority,
        attachment=attachment,
        attachment_name=attachment.name if attachment else '',
    )
    thread.updated_at = timezone.now()
    thread.save(update_fields=['updated_at'])

    # Notification
    SmartNotification.objects.create(
        recipient=receiver,
        notif_type='info',
        category='inbox',
        title=f'Reply: {thread.subject}',
        message=truncatewords(body, 12),
        url=f'/communication/inbox/thread/{thread.pk}/',
    )

    return JsonResponse({
        'id': msg.id,
        'sender_name': user.get_full_name() or user.username,
        'body': msg.body,
        'attachment': msg.attachment.url if msg.attachment else None,
        'attachment_name': msg.attachment_name,
        'priority': msg.priority,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
        'is_mine': True,
    })


@login_required
@require_POST
def inbox_archive(request, message_id):
    """Archive an inbox message."""
    user = request.user
    msg = get_object_or_404(InboxMessage, pk=message_id)

    if msg.sender == user:
        msg.is_archived_by_sender = True
    elif msg.receiver == user:
        msg.is_archived_by_receiver = True
    else:
        return JsonResponse({'error': 'Access denied'}, status=403)

    msg.save()
    return JsonResponse({'success': True})


# ─────────────────────────────────────────────────────────
#  NOTIFICATIONS — AJAX
# ─────────────────────────────────────────────────────────

@login_required
@require_GET
def notifications_api(request):
    """Return unread + recent notifications for the bell dropdown."""
    user = request.user
    notifs = (
        SmartNotification.objects
        .filter(recipient=user)
        .order_by('-created_at')[:15]
    )
    unread_count = SmartNotification.objects.filter(recipient=user, is_read=False).count()

    data = []
    for n in notifs:
        data.append({
            'id': n.id,
            'type': n.notif_type,
            'category': n.category,
            'title': n.title,
            'message': n.message,
            'url': n.url,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({'notifications': data, 'unread_count': unread_count})


@login_required
@require_POST
def notification_mark_read(request, notif_id):
    """Mark a single notification as read."""
    n = get_object_or_404(SmartNotification, pk=notif_id, recipient=request.user)
    n.is_read = True
    n.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def notification_mark_all_read(request):
    """Mark all notifications as read."""
    SmartNotification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'success': True})


# ─────────────────────────────────────────────────────────
#  POLLING endpoint (for future WebSocket replacement)
# ─────────────────────────────────────────────────────────

@login_required
@require_GET
def chat_poll_api(request, conversation_id):
    """Poll for new messages since a given message id."""
    user = request.user
    convo = get_object_or_404(ChatConversation, pk=conversation_id)

    if user != convo.participant1 and user != convo.participant2:
        return JsonResponse({'error': 'Access denied'}, status=403)

    after_id = int(request.GET.get('after', 0))
    new_msgs = (
        convo.messages
        .filter(pk__gt=after_id)
        .exclude(sender=user)
        .select_related('sender')
        .order_by('created_at')
    )

    # Mark as seen
    new_msgs.filter(status__in=['sent', 'delivered']).update(status='seen')

    data = []
    for m in new_msgs:
        data.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.get_full_name() or m.sender.username,
            'body': m.body,
            'attachment': m.attachment.url if m.attachment else None,
            'attachment_name': m.attachment_name,
            'is_image': m.is_image,
            'status': m.status,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_mine': False,
        })

    return JsonResponse({'messages': data})


@login_required
@require_GET
def group_chat_poll_api(request, group_id):
    """Poll for new group chat messages since a given message id."""
    user = request.user
    group = get_object_or_404(Group, pk=group_id)

    if not can_access_group_chat(user, group):
        return JsonResponse({'error': 'Access denied'}, status=403)

    after_id = int(request.GET.get('after', 0))
    new_msgs = (
        group.chat_messages
        .filter(pk__gt=after_id)
        .exclude(sender=user)
        .select_related('sender')
        .order_by('created_at')
    )

    data = []
    for m in new_msgs:
        data.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.get_full_name() or m.sender.username,
            'body': m.body,
            'attachment': m.attachment.url if m.attachment else None,
            'attachment_name': m.attachment_name,
            'is_image': m.is_image,
            'status': m.status,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_mine': False,
        })

    return JsonResponse({'messages': data})
