from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        """
        Import signal receivers when the application registry is fully populated.
        This guarantees that receivers are registered and ready to handle signals.
        """
        import notifications.signals  # noqa: F401
