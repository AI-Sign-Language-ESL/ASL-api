from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tafahom_api.apps.v1.users"
    label = "users"

    def ready(self):
        # This line is required to activate the billing signal!
        import tafahom_api.apps.v1.users.signals  # noqa
