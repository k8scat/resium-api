# Generated by Django 3.0.2 on 2020-02-08 11:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0011_baiduaccount_csdnaccount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baiduaccount',
            name='cookies',
            field=models.TextField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='csdnaccount',
            name='cookies',
            field=models.TextField(default=None, null=True),
        ),
    ]
