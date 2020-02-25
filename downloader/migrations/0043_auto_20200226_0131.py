# Generated by Django 3.0.2 on 2020-02-25 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0042_auto_20200225_2249'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadrecord',
            name='download_device',
            field=models.CharField(default=None, max_length=200, null=True, verbose_name='下载资源时使用的设备'),
        ),
        migrations.AddField(
            model_name='downloadrecord',
            name='download_ip',
            field=models.CharField(default=None, max_length=100, null=True, verbose_name='下载资源时的ip地址'),
        ),
    ]
