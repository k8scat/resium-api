# Generated by Django 3.0.2 on 2020-03-19 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0061_auto_20200317_0824'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resource',
            name='category',
        ),
        migrations.AlterField(
            model_name='resource',
            name='download_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='resource',
            name='file_md5',
            field=models.CharField(default=None, max_length=100, null=True, verbose_name='文件的md5值'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='filename',
            field=models.CharField(default=None, max_length=100, null=True, verbose_name='资源文件名'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='key',
            field=models.CharField(default=None, max_length=200, null=True, unique=True, verbose_name='资源存储文件'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='size',
            field=models.IntegerField(default=None, null=True, verbose_name='资源文件大小'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='tags',
            field=models.CharField(default=None, max_length=240, null=True, verbose_name='资源标签'),
        ),
    ]