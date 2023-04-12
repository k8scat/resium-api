# Generated by Django 3.0.2 on 2020-06-19 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0086_mpswiperad_is_ok'),
    ]

    operations = [
        migrations.AddField(
            model_name='csdnaccount',
            name='qq',
            field=models.CharField(default=None, max_length=20, verbose_name='账号拥有者的QQ号'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='resource',
            name='filename',
            field=models.CharField(default=None, max_length=240, null=True, verbose_name='资源文件名'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='title',
            field=models.CharField(max_length=200, verbose_name='资源标题'),
        ),
    ]
