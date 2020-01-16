from django.db import models


class Base(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        abstract = True


class User(Base):
    email = models.EmailField(verbose_name='邮箱')
    password = models.CharField(max_length=100, verbose_name='密码')
    # 邀请码
    invite_code = models.CharField(max_length=6, verbose_name='邀请码')
    # 受邀请码
    invited_code = models.CharField(max_length=6, verbose_name='受邀请码')
    # 是否激活
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    # 验证码
    code = models.CharField(max_length=6, verbose_name='验证码')
    # 可用总数
    valid_count = models.IntegerField(default=0, verbose_name='可用下载数')
    # 已用总数
    used_count = models.IntegerField(default=0, verbose_name='已用下载数')

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
    pay_url = models.TextField()
    # 购买次数
    purchase_count = models.IntegerField()

    class Meta:
        db_table = 'order'


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 资源地址
    resource_url = models.CharField(max_length=200)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'download_record'


class Service(Base):
    total_amount = models.FloatField()
    purchase_count = models.IntegerField()

    class Meta:
        db_table = 'service'


class Csdnbot(Base):
    status = models.BooleanField()

    class Meta:
        db_table = 'csdnbot'


class Resource(Base):
    csdn_url = models.CharField(max_length=200, null=True, default=None)
    title = models.CharField(max_length=100)
    filename = models.CharField(max_length=100)
    desc = models.TextField()
    size = models.IntegerField()
    category = models.CharField(max_length=100)
    # 存储在oss中的key
    key = models.CharField(max_length=200)

    class Meta:
        db_table = 'resource'


class ResourceTag(Base):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    tag = models.CharField(max_length=50)

    class Meta:
        db_table = 'resource_tag'
