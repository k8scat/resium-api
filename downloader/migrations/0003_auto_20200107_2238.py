# Generated by Django 3.0.2 on 2020-01-07 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0002_auto_20200107_2237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='active',
        ),
        migrations.AddField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
