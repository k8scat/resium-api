# Generated by Django 3.0.2 on 2020-06-13 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0073_auto_20200613_1909'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='qrcode',
            name='user_id',
        ),
        migrations.AddField(
            model_name='qrcode',
            name='uid',
            field=models.CharField(default=None, max_length=50, null=True, verbose_name='扫码登录时保存的uid'),
        ),
    ]