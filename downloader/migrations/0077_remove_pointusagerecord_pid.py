# Generated by Django 3.0.2 on 2020-06-16 04:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0076_article_is_original'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pointusagerecord',
            name='pid',
        ),
    ]