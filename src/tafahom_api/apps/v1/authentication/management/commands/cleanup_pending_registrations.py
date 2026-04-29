from django.core.management.base import BaseCommand
from django.utils import timezone
from tafahom_api.apps.v1.authentication.models import PendingRegistration


class Command(BaseCommand):
    help = 'Clean up expired pending registrations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=30,
            help='Delete pending registrations older than this many minutes (default: 30)',
        )

    def handle(self, *args, **options):
        minutes = options['minutes']
        time_threshold = timezone.now() - timezone.timedelta(minutes=minutes)

        expired_count, _ = PendingRegistration.objects.filter(
            created_at__lt=time_threshold,
            is_verified=False,
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {expired_count} expired pending registration(s)')
        )
