# Generated by Django 3.0.2 on 2020-02-17 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0036_auto_20200217_1853'),
    ]

    operations = [
        migrations.AddField(
            model_name='advert',
            name='title',
            field=models.CharField(default=None, max_length=100, verbose_name='推广标题'),
            preserve_default=False,
        ),
    ]
