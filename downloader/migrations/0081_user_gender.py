# Generated by Django 3.0.2 on 2020-06-17 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0080_service_is_hot'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='gender',
            field=models.BinaryField(default=None, null=True, verbose_name='性别'),
        ),
    ]
