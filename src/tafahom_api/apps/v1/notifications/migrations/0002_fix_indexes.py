from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        # Remove the manually-named indexes from 0001_initial
        migrations.RemoveIndex(
            model_name='notification',
            name='notif_user_created_idx',
        ),
        migrations.RemoveIndex(
            model_name='notification',
            name='notif_user_read_idx',
        ),
        # Re-add without explicit names so Django auto-names them
        # to match what the model's Meta.indexes declaration expects
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', '-created_at']),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read']),
        ),
    ]
