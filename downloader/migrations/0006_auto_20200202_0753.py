# Generated by Django 3.0.2 on 2020-02-01 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0005_remove_coupon_expire_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='wx_openid',
            field=models.CharField(default=None, max_length=200, null=True),
        ),
    ]
