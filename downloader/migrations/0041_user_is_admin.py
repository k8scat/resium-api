# Generated by Django 3.0.2 on 2020-04-29 05:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0040_remove_user_osc_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_admin',
            field=models.BooleanField(default=False, verbose_name='是否是管理员账号'),
        ),
    ]
