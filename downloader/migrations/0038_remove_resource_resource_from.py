# Generated by Django 3.0.2 on 2020-01-29 23:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0037_auto_20200130_0609'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resource',
            name='resource_from',
        ),
    ]
