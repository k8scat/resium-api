# Generated by Django 3.0.2 on 2020-02-08 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0014_auto_20200208_2238'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadrecord',
            name='account',
            field=models.EmailField(default='17770040362@163.com', max_length=254, verbose_name='使用的会员账号'),
            preserve_default=False,
        ),
    ]
