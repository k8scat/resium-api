# Generated by Django 3.0.2 on 2020-06-17 05:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0079_pointrecord_is_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='is_hot',
            field=models.BooleanField(default=False, verbose_name='活动'),
        ),
    ]
