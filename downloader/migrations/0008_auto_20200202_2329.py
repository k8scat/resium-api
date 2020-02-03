# Generated by Django 3.0.2 on 2020-02-02 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0007_user_is_downloading'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='is_deleted',
        ),
        migrations.RemoveField(
            model_name='order',
            name='is_deleted',
        ),
        migrations.AlterField(
            model_name='coupon',
            name='code',
            field=models.CharField(max_length=50, verbose_name='优惠券唯一编码'),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='comment',
            field=models.CharField(max_length=100, null=True, verbose_name='备注'),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='is_used',
            field=models.BooleanField(default=False, verbose_name='是否使用'),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='purchase_count',
            field=models.IntegerField(verbose_name='下载次数'),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='total_amount',
            field=models.FloatField(verbose_name='总金额'),
        ),
        migrations.AlterField(
            model_name='downloadrecord',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='是否被删除'),
        ),
        migrations.AlterField(
            model_name='downloadrecord',
            name='resource_url',
            field=models.CharField(max_length=200, verbose_name='资源地址'),
        ),
        migrations.AlterField(
            model_name='downloadrecord',
            name='title',
            field=models.CharField(max_length=100, verbose_name='资源名称'),
        ),
        migrations.AlterField(
            model_name='order',
            name='out_trade_no',
            field=models.CharField(max_length=50, unique=True, verbose_name='订单号'),
        ),
        migrations.AlterField(
            model_name='order',
            name='paid_time',
            field=models.DateTimeField(null=True, verbose_name='支付时间'),
        ),
        migrations.AlterField(
            model_name='order',
            name='pay_url',
            field=models.TextField(verbose_name='支付地址'),
        ),
        migrations.AlterField(
            model_name='order',
            name='purchase_count',
            field=models.IntegerField(verbose_name='下载次数'),
        ),
        migrations.AlterField(
            model_name='order',
            name='subject',
            field=models.CharField(max_length=50, verbose_name='订单名称'),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_amount',
            field=models.FloatField(verbose_name='总金额'),
        ),
        migrations.AlterField(
            model_name='service',
            name='purchase_count',
            field=models.IntegerField(verbose_name='下载次数'),
        ),
        migrations.AlterField(
            model_name='service',
            name='total_amount',
            field=models.FloatField(verbose_name='总金额'),
        ),
        migrations.AlterField(
            model_name='user',
            name='has_subscribed',
            field=models.BooleanField(default=False, verbose_name='是否关注微信公众号'),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_downloading',
            field=models.BooleanField(default=False, verbose_name='是否正在下载'),
        ),
        migrations.AlterField(
            model_name='user',
            name='return_invitor',
            field=models.BooleanField(default=False, verbose_name='是否返还邀请人优惠券'),
        ),
        migrations.AlterField(
            model_name='user',
            name='wx_openid',
            field=models.CharField(default=None, max_length=200, null=True, verbose_name='微信用户唯一标识'),
        ),
    ]