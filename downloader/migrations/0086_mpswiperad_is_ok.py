# Generated by Django 3.0.2 on 2020-06-17 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0085_mpswiperad'),
    ]

    operations = [
        migrations.AddField(
            model_name='mpswiperad',
            name='is_ok',
            field=models.BooleanField(default=True, verbose_name='是否展示'),
        ),
    ]
