# Generated by Django 3.0.2 on 2020-02-29 11:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0044_student'),
    ]

    operations = [
        migrations.RenameField(
            model_name='student',
            old_name='class',
            new_name='cls',
        ),
    ]