# Generated by Django 3.0.2 on 2020-01-14 07:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0014_auto_20200111_1611'),
    ]

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('update_time', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=100, unique=True)),
                ('filename', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(max_length=200)),
            ],
            options={
                'db_table': 'resource',
            },
        ),
        migrations.CreateModel(
            name='ResourceTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('update_time', models.DateTimeField(auto_now=True)),
                ('tag', models.CharField(max_length=50)),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.Resource')),
            ],
            options={
                'db_table': 'resource_tag',
            },
        ),
    ]
