# Generated by Django 5.2 on 2025-05-10 09:30

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChallengeDeployment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('last_activity', models.DateTimeField(default=django.utils.timezone.now)),
                ('has_active_connections', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Deployment',
                'verbose_name_plural': 'Deployments',
            },
        ),
        migrations.CreateModel(
            name='ChallengeTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folder', models.CharField(help_text='Folder name in game-templates directory', max_length=128, null=True, unique=True)),
                ('name', models.CharField(blank=True, max_length=64, null=True)),
                ('title', models.CharField(blank=True, default='', max_length=256)),
                ('description', models.TextField(blank=True, default='')),
                ('docker_compose', models.TextField(blank=True, default='')),
                ('containers_config', models.JSONField(blank=True, default=dict, null=True)),
                ('networks_config', models.JSONField(blank=True, default=dict, null=True)),
                ('template_file', models.FileField(blank=True, help_text='Upload a zip file containing the scenario folder', null=True, upload_to='ctf/static/uploads/')),
            ],
            options={
                'verbose_name': 'Template',
                'verbose_name_plural': 'Templates',
            },
        ),
        migrations.CreateModel(
            name='ChallengeContainer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, unique=True)),
                ('template_name', models.CharField(blank=True, default='', max_length=128)),
                ('docker_id', models.CharField(max_length=128, unique=True)),
                ('status', models.CharField(choices=[('created', 'Created'), ('running', 'Running'), ('stopped', 'Stopped'), ('deleted', 'Deleted'), ('error', 'Error')], default='created', max_length=16)),
                ('port', models.IntegerField(blank=True, null=True)),
                ('services', models.JSONField(default=list)),
                ('is_entrypoint', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_activity', models.DateTimeField(default=django.utils.timezone.now)),
                ('blue_team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blue_containers', to='accounts.team')),
                ('red_team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='red_containers', to='accounts.team')),
                ('deployment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='containers', to='challenges.challengedeployment')),
            ],
            options={
                'verbose_name': 'Container',
                'verbose_name_plural': 'Containers',
            },
        ),
        migrations.CreateModel(
            name='ChallengeNetworkConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=128)),
                ('subnet', models.GenericIPAddressField()),
                ('containers', models.ManyToManyField(related_name='challenge_network_configs', to='challenges.challengecontainer')),
                ('deployment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='networks', to='challenges.challengedeployment')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='challenges.challengetemplate')),
            ],
            options={
                'verbose_name': 'Network Config',
                'verbose_name_plural': 'Network Configs',
            },
        ),
        migrations.AddField(
            model_name='challengedeployment',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='deployments', to='challenges.challengetemplate'),
        ),
        migrations.CreateModel(
            name='DeploymentAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(blank=True, max_length=256, null=True)),
                ('access_type', models.CharField(max_length=50)),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('duration', models.DurationField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('containers', models.JSONField(default=list, help_text='List of container IDs accessed during this session')),
                ('deployment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_records', to='challenges.challengedeployment')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.team')),
            ],
            options={
                'verbose_name': 'Deployment Access',
                'verbose_name_plural': 'Deployment Accesses',
                'ordering': ['-start_time'],
            },
        ),
        migrations.AddIndex(
            model_name='challengecontainer',
            index=models.Index(fields=['docker_id'], name='challenges__docker__d5a977_idx'),
        ),
        migrations.AddIndex(
            model_name='challengecontainer',
            index=models.Index(fields=['status'], name='challenges__status_4698a8_idx'),
        ),
        migrations.AddIndex(
            model_name='challengecontainer',
            index=models.Index(fields=['last_activity'], name='challenges__last_ac_da22cb_idx'),
        ),
        migrations.AddIndex(
            model_name='deploymentaccess',
            index=models.Index(fields=['deployment', 'is_active'], name='challenges__deploym_5bc1c0_idx'),
        ),
    ]
