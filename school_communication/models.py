"""
Communication System Models
============================
Covers: Chat (1-to-1 & Group), Internal Inbox, and Smart Notifications.
Designed for future WebSocket / Django Channels upgrade.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


# ─────────────────────────────────────────────
#  CHAT SYSTEM
# ─────────────────────────────────────────────

class ChatConversation(models.Model):
    """
    A one-to-one conversation thread between exactly two users.
    We always store participant1_id < participant2_id so the pair is unique.
    """
    participant1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_p1',
    )
    participant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_p2',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('participant1', 'participant2')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['participant1', 'participant2']),
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        return f"Chat: {self.participant1} ↔ {self.participant2}"

    def other_user(self, user):
        """Return the other participant given one user."""
        return self.participant2 if self.participant1 == user else self.participant1

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class ChatMessage(models.Model):
    """
    A single message within a one-to-one conversation.
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('seen', 'Seen'),
    ]
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_chat_messages',
    )
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/%Y/%m/', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        preview = self.body[:40] if self.body else '[attachment]'
        return f"{self.sender}: {preview}"

    @property
    def is_image(self):
        if self.attachment:
            name = self.attachment.name.lower()
            return name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        return False


class GroupChatMessage(models.Model):
    """
    A message in a Group chat room.
    The Group model already exists in classes app — we link to it.
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
    ]
    group = models.ForeignKey(
        'classes.Group',
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_group_messages',
    )
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to='group_chat_attachments/%Y/%m/', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', 'created_at']),
        ]

    def __str__(self):
        preview = self.body[:40] if self.body else '[attachment]'
        return f"[{self.group}] {self.sender}: {preview}"

    @property
    def is_image(self):
        if self.attachment:
            name = self.attachment.name.lower()
            return name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        return False


# ─────────────────────────────────────────────
#  INTERNAL INBOX (EMAIL-LIKE SYSTEM)
# ─────────────────────────────────────────────

class InboxThread(models.Model):
    """
    A conversation thread (like an email thread).
    Holds the subject and connects multiple InboxMessage replies.
    """
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.subject

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class InboxMessage(models.Model):
    """
    A single message within an inbox thread (supports replies).
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    thread = models.ForeignKey(
        InboxThread,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_inbox_messages',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_inbox_messages',
    )
    body = models.TextField()
    attachment = models.FileField(upload_to='inbox_attachments/%Y/%m/', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_read = models.BooleanField(default=False)
    is_archived_by_sender = models.BooleanField(default=False)
    is_archived_by_receiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['receiver', 'is_read']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['thread', 'created_at']),
        ]

    def __str__(self):
        return f"Inbox: {self.sender} → {self.receiver} | {self.thread.subject}"


# ─────────────────────────────────────────────
#  SMART NOTIFICATION SYSTEM
# ─────────────────────────────────────────────

class SmartNotification(models.Model):
    """
    Global notification system linked to events across the app.
    """
    NOTIF_TYPE_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    CATEGORY_CHOICES = [
        ('chat', 'New Chat Message'),
        ('inbox', 'New Inbox Message'),
        ('report', 'Report Submitted'),
        ('justification', 'Justification Submitted'),
        ('report_priority', 'High Priority Report'),
        ('justification_pending', 'Justification Pending'),
        ('absence_alert', 'Absence Alert'),
        ('system', 'System'),
    ]
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='smart_notifications',
    )
    notif_type = models.CharField(max_length=10, choices=NOTIF_TYPE_CHOICES, default='info')
    category = models.CharField(max_length=25, choices=CATEGORY_CHOICES, default='system')
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True, help_text="Redirect URL when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.notif_type}] {self.title} → {self.recipient}"
