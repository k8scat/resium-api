# Generated by Django 3.0.2 on 2020-04-16 15:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0023_auto_20200416_2237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='downloadrecord',
            name='download_device',
        ),
        migrations.RemoveField(
            model_name='downloadrecord',
            name='download_ip',
        ),
    ]
