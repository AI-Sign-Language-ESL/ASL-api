from django.apps import AppConfig

class YoutubeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tafahom_api.apps.v1.youtube'
    label = 'youtube_v1'

    def ready(self):
        # Reset stuck processing translations on server restart
        import sys
        # Avoid running during makemigrations or collectstatic
        if 'runserver' in sys.argv or 'daphne' in sys.argv[0]:
            try:
                from .models import YouTubeTranslation
                from django.db import transaction
                
                with transaction.atomic():
                    stuck_count = YouTubeTranslation.objects.filter(status='processing').update(status='failed')
                    if stuck_count > 0:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Reset {stuck_count} stuck YouTube translations from 'processing' to 'failed'.")
            except Exception:
                pass
