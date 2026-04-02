import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings.base")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DROP TABLE IF EXISTS credit_transactions;")
    cursor.execute("DROP TABLE IF EXISTS token_transactions;")
    cursor.execute("DROP TABLE IF EXISTS subscriptions;")
    cursor.execute("DROP TABLE IF EXISTS subscription_plans;")
    cursor.execute("DELETE FROM django_migrations WHERE app='billing';")
    print("Dropped billing tables.")
