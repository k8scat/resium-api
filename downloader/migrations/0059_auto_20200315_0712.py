# Generated by Django 3.0.2 on 2020-03-14 23:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0058_resource_zhiwang_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='csdnaccount',
            name='github_password',
        ),
        migrations.RemoveField(
            model_name='csdnaccount',
            name='github_username',
        ),
        migrations.RemoveField(
            model_name='csdnaccount',
            name='phone',
        ),
        migrations.RemoveField(
            model_name='csdnaccount',
            name='username',
        ),
        migrations.AlterField(
            model_name='user',
            name='login_device',
            field=models.TextField(default=None, null=True, verbose_name='登录设备'),
        ),
    ]