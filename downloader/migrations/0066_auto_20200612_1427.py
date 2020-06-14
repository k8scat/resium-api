# Generated by Django 3.0.2 on 2020-06-12 06:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0065_remove_user_github_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='csdnaccount',
            name='email',
        ),
        migrations.RemoveField(
            model_name='user',
            name='is_pattern',
        ),
        migrations.AddField(
            model_name='csdnaccount',
            name='unit_price',
            field=models.FloatField(default=0.6, verbose_name='CSDN单次下载价格'),
        ),
    ]