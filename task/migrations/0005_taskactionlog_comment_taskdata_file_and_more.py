# Generated by Django 5.1.1 on 2025-05-17 08:08

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('process', '0006_alter_action_action_type_alter_processfield_order_and_more'),
        ('task', '0004_delete_taskuser'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='taskactionlog',
            name='comment',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskdata',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='task_files/'),
        ),
        migrations.AlterField(
            model_name='taskactionlog',
            name='action',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='process.action'),
        ),
        migrations.AlterField(
            model_name='taskactionlog',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='task.task'),
        ),
        migrations.AlterField(
            model_name='taskactionlog',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
    ]
