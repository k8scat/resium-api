# Generated by Django 3.0.2 on 2020-05-11 12:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0056_csdnaccount_is_upload_account'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='baidu_openid',
        ),
        migrations.RemoveField(
            model_name='user',
            name='coding_user_id',
        ),
        migrations.RemoveField(
            model_name='user',
            name='dingtalk_openid',
        ),
        migrations.CreateModel(
            name='PointUsageRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('pid', models.CharField(max_length=100, unique=True, verbose_name='积分使用记录唯一标识')),
                ('point', models.IntegerField()),
                ('comment', models.CharField(max_length=100, verbose_name='积分使用备注')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='downloader.User')),
            ],
            options={
                'db_table': 'point_usage_record',
            },
        ),
    ]
