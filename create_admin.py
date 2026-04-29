"""
Script to create admin and supervisor users via Django shell
Run: python manage.py shell < create_admin.py
"""
from django.contrib.auth import get_user_model
from tafahom_api.apps.v1.users.models import User as UserModel

User = get_user_model()

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
    print(f'Created admin user: {admin.username}')
else:
    print('Admin user already exists')

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
    print(f'Created supervisor user: {supervisor.username}')
else:
    print('Supervisor user already exists')

print('\nDone!')
print('Admin: username=admin, password=admin123')
print('Supervisor: username=supervisor, password=supervisor123')
