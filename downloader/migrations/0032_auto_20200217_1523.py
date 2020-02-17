# Generated by Django 3.0.2 on 2020-02-17 07:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0031_user_nickname'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='是否被删除'),
        ),
        migrations.AlterField(
            model_name='order',
            name='coupon',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='downloader.Coupon', verbose_name='使用的优惠券'),
        ),
    ]
