from django.db import models


class Base(models.Model):
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(Base):
    email = models.EmailField()
    password = models.CharField(max_length=100)
    # 邀请码
    invite_code = models.CharField(max_length=6)
    # 受邀请码
    invited_code = models.CharField(max_length=6)
    # 是否激活
    is_active = models.BooleanField(default=False)
    # 验证码
    code = models.CharField(max_length=6)
    # 可用总数
    valid_count = models.IntegerField(default=0)
    # 已用总数
    used_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'user'


class Order(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 订单名称
    subject = models.CharField(max_length=50)
    # 唯一订单号
    out_trade_no = models.CharField(max_length=50, unique=True)
    # 总金额
    total_amount = models.FloatField()
    # 支付时间
    paid_time = models.DateTimeField(null=True)
    # 订单备注
    comment = models.CharField(max_length=100)
    pay_url = models.TextField()

    class Meta:
        db_table = 'order'


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 资源地址
    resource_url = models.CharField(max_length=200)

    class Meta:
        db_table = 'download_record'
