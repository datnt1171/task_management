# Generated by Django 5.1.1 on 2025-05-03 09:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workflow_engine', '0002_state_is_first_state_state_is_last_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='state',
            name='is_first_state',
        ),
        migrations.RemoveField(
            model_name='state',
            name='is_last_state',
        ),
    ]
