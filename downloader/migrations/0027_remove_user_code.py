# Generated by Django 3.0.2 on 2020-04-17 04:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0026_auto_20200417_1042'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='code',
        ),
    ]
