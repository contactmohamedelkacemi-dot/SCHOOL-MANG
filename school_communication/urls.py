from django.urls import path
from . import views

app_name = 'school_communication'

urlpatterns = [
    # ── Chat ──────────────────────────────────────
    path('chat/', views.chat_home, name='chat_home'),
    path('chat/start/', views.chat_start_api, name='chat_start'),
    path('chat/<int:conversation_id>/messages/', views.chat_messages_api, name='chat_messages'),
    path('chat/<int:conversation_id>/send/', views.chat_send_api, name='chat_send'),
    path('chat/<int:conversation_id>/poll/', views.chat_poll_api, name='chat_poll'),

    # ── Group Chat ────────────────────────────────
    path('chat/group/<int:group_id>/messages/', views.group_chat_messages_api, name='group_chat_messages'),
    path('chat/group/<int:group_id>/send/', views.group_chat_send_api, name='group_chat_send'),
    path('chat/group/<int:group_id>/poll/', views.group_chat_poll_api, name='group_chat_poll'),

    # ── Inbox ─────────────────────────────────────
    path('inbox/', views.inbox_home, name='inbox_home'),
    path('inbox/compose/', views.inbox_compose, name='inbox_compose'),
    path('inbox/thread/<int:thread_id>/', views.inbox_thread_detail, name='inbox_thread_detail'),
    path('inbox/thread/<int:thread_id>/reply/', views.inbox_reply, name='inbox_reply'),
    path('inbox/archive/<int:message_id>/', views.inbox_archive, name='inbox_archive'),

    # ── Notifications ─────────────────────────────
    path('notifications/', views.notifications_api, name='notifications_api'),
    path('notifications/<int:notif_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
]
