# Generated by Django 3.0.2 on 2020-04-01 20:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0012_auto_20200402_0412'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='check_in_count',
        ),
    ]
