from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin and supervisor users'

    def handle(self, *args, **options):
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@tafahom.io',
                password='admin123',
                role='admin',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS('Created admin user: admin / admin123'))
        else:
            self.stdout.write('Admin user already exists')

        # Create supervisor user
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
        self.stdout.write('Admin: username=admin, password=admin123')
        self.stdout.write('Supervisor: username=supervisor, password=supervisor123')
