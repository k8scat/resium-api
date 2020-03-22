# Generated by Django 3.0.2 on 2020-03-21 23:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0074_docerpreviewimage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='docerpreviewimage',
            name='resource',
        ),
        migrations.AddField(
            model_name='docerpreviewimage',
            name='resource_url',
            field=models.CharField(default=None, max_length=240, verbose_name='资源地址'),
            preserve_default=False,
        ),
    ]
