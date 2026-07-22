from django.contrib import admin
from .models import (
    ChatConversation, ChatMessage, GroupChatMessage,
    InboxThread, InboxMessage, SmartNotification,
)


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant1', 'participant2', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('participant1__username', 'participant2__username')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('body',)


@admin.register(GroupChatMessage)
class GroupChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'sender', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('body',)


@admin.register(InboxThread)
class InboxThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'created_at', 'updated_at')
    search_fields = ('subject',)


@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread', 'sender', 'receiver', 'priority', 'is_read', 'created_at')
    list_filter = ('priority', 'is_read', 'created_at')
    search_fields = ('body', 'thread__subject')


@admin.register(SmartNotification)
class SmartNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'notif_type', 'category', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'category', 'is_read', 'created_at')
    search_fields = ('title', 'message')
