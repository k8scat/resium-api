# Generated by Django 3.0.2 on 2020-02-01 23:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0004_delete_csdnbot'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='expire_time',
        ),
    ]