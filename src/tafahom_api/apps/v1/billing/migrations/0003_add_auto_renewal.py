# Generated manually to add missing auto_renewal field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='auto_renewal',
            field=models.BooleanField(default=True),
        ),
    ]
