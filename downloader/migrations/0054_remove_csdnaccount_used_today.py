# Generated by Django 3.0.2 on 2020-03-05 20:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0053_auto_20200306_0312'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='csdnaccount',
            name='used_today',
        ),
    ]
