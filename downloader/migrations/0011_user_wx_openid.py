# Generated by Django 3.0.2 on 2020-04-01 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0010_remove_user_github_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='wx_openid',
            field=models.CharField(default=None, max_length=240, null=True),
        ),
    ]