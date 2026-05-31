from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_fix_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('contribution_submitted', 'Contribution Submitted'), ('contribution_approved', 'Contribution Approved'), ('contribution_rejected', 'Contribution Rejected'), ('tokens', 'Tokens'), ('meeting_invite', 'Meeting Invite'), ('subscription', 'Subscription'), ('general', 'General'), ('youtube', 'YouTube')], default='general', max_length=50),
        ),
    ]
