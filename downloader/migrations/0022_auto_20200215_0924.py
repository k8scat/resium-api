# Generated by Django 3.0.2 on 2020-02-15 01:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0021_auto_20200215_0830'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='has_subscribed',
        ),
        migrations.RemoveField(
            model_name='user',
            name='wx_openid',
        ),
    ]