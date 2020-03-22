# Generated by Django 3.0.2 on 2020-03-21 22:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0072_remove_user_phone'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_downloading',
        ),
        migrations.AddField(
            model_name='doceraccount',
            name='month_used_count',
            field=models.IntegerField(default=0, verbose_name='当月已使用VIP下载数'),
        ),
        migrations.AddField(
            model_name='resource',
            name='is_docer_vip_doc',
            field=models.BooleanField(default=False, verbose_name='是否是稻壳VIP文档'),
        ),
    ]