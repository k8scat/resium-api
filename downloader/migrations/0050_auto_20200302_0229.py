# Generated by Django 3.0.2 on 2020-03-01 18:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0049_doceraccount'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone',
            field=models.CharField(default=None, max_length=20, null=True, verbose_name='手机号'),
        ),
        migrations.AddField(
            model_name='user',
            name='student',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='downloader.Student'),
        ),
    ]
