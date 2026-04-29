import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin and supervisor users from environment variables'

    def handle(self, *args, **options):
        # Get credentials from environment variables with defaults
        admin_username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        admin_email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@tafahom.io')
        admin_password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

        # Create admin user
        if not User.objects.filter(username=admin_username).exists():
            admin = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role='admin',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_username} / {admin_password}'))
        else:
            self.stdout.write(f'Admin user {admin_username} already exists')

        # Create supervisor user (fixed credentials)
        if not User.objects.filter(username='supervisor').exists():
            supervisor = User.objects.create_user(
                username='supervisor',
                email='supervisor@tafahom.io',
                password='supervisor123',
                role='supervisor',
                first_name='Supervisor',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS('Created supervisor user: supervisor / supervisor123'))
        else:
            self.stdout.write('Supervisor user already exists')

        self.stdout.write(self.style.WARNING('\nCredentials:'))
        self.stdout.write(f'Admin: username={admin_username}, password={admin_password}')
        self.stdout.write('Supervisor: username=supervisor, password=supervisor123')
