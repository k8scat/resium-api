# Generated by Django 3.0.2 on 2020-07-01 14:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0092_auto_20200625_1814'),
    ]

    operations = [
        migrations.CreateModel(
            name='Talk',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('content', models.TextField()),
                ('is_delete', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.User')),
            ],
            options={
                'db_table': 'talk',
            },
        ),
        migrations.CreateModel(
            name='TalkComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('content', models.TextField()),
                ('talk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.Talk')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.User')),
            ],
            options={
                'db_table': 'talk_comment',
            },
        ),
        migrations.CreateModel(
            name='TalkImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('url', models.CharField(max_length=240)),
                ('talk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.Talk')),
            ],
            options={
                'db_table': 'talk_image',
            },
        ),
        migrations.CreateModel(
            name='TalkLike',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('talk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.Talk')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='downloader.User')),
            ],
            options={
                'db_table': 'talk_like',
            },
        ),
        migrations.DeleteModel(
            name='PudnAccount',
        ),
        migrations.DeleteModel(
            name='SystemInfo',
        ),
        migrations.AlterField(
            model_name='articlecomment',
            name='content',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='resourcecomment',
            name='content',
            field=models.TextField(),
        ),
    ]