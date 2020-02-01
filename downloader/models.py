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
    # 是否给过邀请人优惠券
    return_invitor = models.BooleanField(default=False)
    # 是否激活
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    # 验证码
    code = models.CharField(max_length=6, verbose_name='验证码')
    # 可用总数
    valid_count = models.IntegerField(default=0, verbose_name='可用下载数')
    # 已用总数
    used_count = models.IntegerField(default=0, verbose_name='已用下载数')
    wx_openid = models.CharField(max_length=200)

    class Meta:
        db_table = 'user'


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 资源地址
    resource_url = models.CharField(max_length=200)
    is_deleted = models.BooleanField(default=False)
    title = models.CharField(max_length=100)

    class Meta:
        db_table = 'download_record'


class Service(Base):
    total_amount = models.FloatField()
    purchase_count = models.IntegerField()

    class Meta:
        db_table = 'service'


class Csdnbot(Base):
    is_healthy = models.BooleanField()
    wx_access_token = models.TextField()

    class Meta:
        db_table = 'csdnbot'


class Resource(Base):
    # 资源地址，如果是上传资源，则留空
    url = models.CharField(max_length=200, null=True, default=None, verbose_name='资源地址')
    title = models.CharField(max_length=100, verbose_name='资源标题')
    filename = models.CharField(max_length=100, verbose_name='资源文件名')
    desc = models.TextField(null=True, default=None, verbose_name='资源描述')
    size = models.IntegerField(verbose_name='资源文件大小')
    category = models.CharField(max_length=100, verbose_name='资源分类')
    # 存储在oss中的key
    key = models.CharField(max_length=200, verbose_name='资源存储文件')
    # 以 !sep! 分离
    tags = models.CharField(max_length=240, verbose_name='资源标签')

    class Meta:
        db_table = 'resource'


class Coupon(Base):
    """
    优惠券
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.FloatField()
    purchase_count = models.IntegerField()
    is_used = models.BooleanField(default=False)
    expire_time = models.DateTimeField()
    # 优惠券唯一编码
    code = models.CharField(max_length=50)
    comment = models.CharField(max_length=100, null=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'coupon'


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
    is_deleted = models.BooleanField(default=False)
    coupon = models.OneToOneField(Coupon, on_delete=models.DO_NOTHING, null=True)

    class Meta:
        db_table = 'order'
