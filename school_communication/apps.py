from django.apps import AppConfig


class SchoolCommunicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'school_communication'
    verbose_name = 'Communication System'

    def ready(self):
        import school_communication.signals  # noqa: F401
