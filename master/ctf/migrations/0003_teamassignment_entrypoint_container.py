# Generated by Django 5.2 on 2025-05-11 11:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0001_initial'),
        ('ctf', '0002_flaghintusage'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamassignment',
            name='entrypoint_container',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='challenges.challengecontainer'),
        ),
    ]
