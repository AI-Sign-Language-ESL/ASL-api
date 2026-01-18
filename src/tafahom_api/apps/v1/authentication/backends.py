from django.contrib.auth.backends import ModelBackend
from tafahom_api.apps.v1.users.models import User


class EmailOrUsernameBackend(ModelBackend):
    """
    NU-Quran style:
    - Accepts email OR username in the same field
    - Delegates permission checks to ModelBackend
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        user = (
            User.objects.filter(username__iexact=username).first()
            or User.objects.filter(email__iexact=username).first()
        )

        if not user:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
