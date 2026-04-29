import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin and supervisor users from environment variables'

    def handle(self, *args, **options):
        # ===== Admin ENV =====
        admin_username = (os.getenv('DJANGO_SUPERUSER_USERNAME') or 'admin').strip()
        admin_email = (os.getenv('DJANGO_SUPERUSER_EMAIL') or 'admin@tafahom.io').strip()
        admin_password = os.getenv('DJANGO_SUPERUSER_PASSWORD') or 'admin123'

        # ===== Supervisor ENV (optional but better) =====
        supervisor_username = (os.getenv('SUPERVISOR_USERNAME') or 'supervisor').strip()
        supervisor_email = (os.getenv('SUPERVISOR_EMAIL') or 'supervisor@tafahom.io').strip()
        supervisor_password = os.getenv('SUPERVISOR_PASSWORD') or 'supervisor123'

        # =========================
        # Create / Update Admin
        # =========================
        admin, _ = User.objects.get_or_create(username=admin_username)

        admin.email = admin_email
        admin.role = 'admin'
        admin.first_name = 'Admin'
        admin.last_name = 'User'
        admin.is_verified = True
        admin.is_superuser = True
        admin.is_staff = True
        admin.set_password(admin_password)
        admin.save()

        self.stdout.write(self.style.SUCCESS(f'Admin ready: {admin_username}'))

        # =========================
        # Create / Update Supervisor
        # =========================
        supervisor, _ = User.objects.get_or_create(username=supervisor_username)

        supervisor.email = supervisor_email
        supervisor.role = 'supervisor'
        supervisor.first_name = 'Supervisor'
        supervisor.last_name = 'User'
        supervisor.is_verified = True
        supervisor.set_password(supervisor_password)
        supervisor.save()

        self.stdout.write(self.style.SUCCESS(f'Supervisor ready: {supervisor_username}'))