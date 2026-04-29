import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin and supervisor users from environment variables'

    def handle(self, *args, **options):
        admin_username = (os.getenv('DJANGO_SUPERUSER_USERNAME') or 'admin').strip()
        admin_email = (os.getenv('DJANGO_SUPERUSER_EMAIL') or 'admin@tafahom.io').strip()
        admin_password = os.getenv('DJANGO_SUPERUSER_PASSWORD') or 'admin123'

        if not admin_username:
            admin_username = 'admin'

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

        supervisor, _ = User.objects.get_or_create(username='supervisor')

        supervisor.email = 'supervisor@tafahom.io'
        supervisor.role = 'supervisor'
        supervisor.first_name = 'Supervisor'
        supervisor.last_name = 'User'
        supervisor.is_verified = True
        supervisor.set_password('supervisor123')
        supervisor.save()

        self.stdout.write(self.style.SUCCESS('Supervisor ready: supervisor'))