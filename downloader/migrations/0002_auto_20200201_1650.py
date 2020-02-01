# Generated by Django 3.0.2 on 2020-02-01 08:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='csdnbot',
            old_name='status',
            new_name='is_healthy',
        ),
        migrations.AddField(
            model_name='csdnbot',
            name='wx_access_token',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
    ]