# Generated by Django 3.0.2 on 2020-05-02 16:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0050_qrcode_code_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='FreeDownloadCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('code', models.CharField(max_length=20)),
                ('is_used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='downloader.User')),
            ],
            options={
                'db_table': 'free_download_code',
            },
        ),
    ]