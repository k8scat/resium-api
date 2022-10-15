from django.db import models

from downloader.models import Base
from downloader.models.user import User


class Order(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=50, verbose_name="订单名称")
    out_trade_no = models.CharField(max_length=50, unique=True, verbose_name="订单号")
    total_amount = models.FloatField(verbose_name="总金额")
    has_paid = models.BooleanField(default=False, verbose_name="是否支付")
    pay_url = models.TextField(default=None, null=True, verbose_name="支付地址，小程序微信支付时不存在")
    point = models.IntegerField(verbose_name="下载积分")
    is_deleted = models.BooleanField(default=False, verbose_name="是否被删除")

    class Meta:
        db_table = "order"
