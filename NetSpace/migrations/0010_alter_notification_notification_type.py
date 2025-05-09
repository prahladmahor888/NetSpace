# Generated by Django 5.1.7 on 2025-04-20 19:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('NetSpace', '0009_notification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('follow_request', 'Follow Request'), ('follow_accept', 'Follow Request Accepted'), ('follow_back', 'Follow Back'), ('follow_request_rejected', 'Follow Request Rejected'), ('new_follower', 'New Follower'), ('unfollow', 'Unfollowed')], max_length=50),
        ),
    ]
