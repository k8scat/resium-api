# Generated by Django 3.0.2 on 2020-04-19 04:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0035_user_coding_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='csdnaccount',
            name='need_sms_validate',
            field=models.BooleanField(default=False, verbose_name='是否需要短信验证'),
        ),
    ]
