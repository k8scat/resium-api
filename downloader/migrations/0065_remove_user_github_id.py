# Generated by Django 3.0.2 on 2020-06-12 00:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0064_auto_20200612_0631'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='github_id',
        ),
    ]
