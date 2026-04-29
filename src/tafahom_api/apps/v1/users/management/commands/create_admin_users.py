import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin and supervisor users from environment variables'

    def handle(self, *args, **options):
        # Get credentials from environment variables with defaults
        admin_username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin').strip()
        admin_email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@tafahom.io').strip()
        admin_password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

        # Ensure username is set
        if not admin_username:
            admin_username = 'admin'

        # Create admin user
        admin, created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                'email': admin_email,
                'role': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_verified': True,
                'is_superuser': True,
                'is_staff': True,
            }
        )
        
        if created:
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_username} / {admin_password}'))
        else:
            admin.is_verified = True
            admin.is_superuser = True
            admin.is_staff = True
            admin.save()
            self.stdout.write(f'Admin user {admin_username} already exists (updated as verified/superuser)')

        # Create supervisor user
        supervisor, created = User.objects.get_or_create(
            username='supervisor',
            defaults={
                'email': 'supervisor@tafahom.io',
                'role': 'supervisor',
                'first_name': 'Supervisor',
                'last_name': 'User',
                'is_verified': True,
            }
        )
        
        if created:
            supervisor.set_password('supervisor123')
            supervisor.save()
            self.stdout.write(self.style.SUCCESS('Created supervisor user: supervisor / supervisor123'))
        else:
            supervisor.is_verified = True
            supervisor.save()
            self.stdout.write('Supervisor user already exists (updated as verified)')

        self.stdout.write(self.style.WARNING('\nCredentials:'))
        self.stdout.write(f'Admin: username={admin_username}, password={admin_password}')
        self.stdout.write('Supervisor: username=supervisor, password=supervisor123')
