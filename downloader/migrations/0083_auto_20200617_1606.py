# Generated by Django 3.0.2 on 2020-06-17 08:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0082_auto_20200617_1602'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='city',
            field=models.CharField(default=None, max_length=100, null=True, verbose_name='城市'),
        ),
        migrations.AddField(
            model_name='user',
            name='province',
            field=models.CharField(default=None, max_length=100, null=True, verbose_name='省份'),
        ),
    ]
