import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(
                    choices=[
                        ('contribution_approved', 'Contribution Approved'),
                        ('contribution_rejected', 'Contribution Rejected'),
                        ('tokens', 'Tokens'),
                        ('meeting_invite', 'Meeting Invite'),
                        ('subscription', 'Subscription'),
                        ('general', 'General'),
                    ],
                    default='general',
                    max_length=50,
                )),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('action_url', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'notifications',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='notif_user_created_idx'),
                    models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
                ],
            },
        ),
    ]
