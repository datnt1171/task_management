# Generated by Django 5.1.1 on 2025-05-26 03:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_alter_user_department_alter_user_role'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='manager',
            new_name='supervisor',
        ),
        migrations.AlterField(
            model_name='user',
            name='department',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='user.department'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='user.role'),
            preserve_default=False,
        ),
    ]
