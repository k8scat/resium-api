# Generated by Django 3.0.2 on 2020-02-25 03:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0039_auto_20200224_1842'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='login_device',
            field=models.CharField(default=None, max_length=200, null=True, verbose_name='登录设备'),
        ),
    ]