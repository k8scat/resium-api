# Generated by Django 3.0.2 on 2020-08-08 19:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0098_auto_20200725_1511'),
    ]

    operations = [
        migrations.AlterField(
            model_name='docerpreviewimage',
            name='alt',
            field=models.TextField(verbose_name='图片解释'),
        ),
    ]
