# Generated by Django 3.0.2 on 2020-02-12 01:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0017_auto_20200212_0944'),
    ]

    operations = [
        migrations.AddField(
            model_name='baiduaccount',
            name='is_enabled',
            field=models.BooleanField(default=True, verbose_name='是否使用该账号'),
        ),
    ]