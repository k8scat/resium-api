from django.db import models


class Base(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        abstract = True


class User(Base):
    email = models.EmailField(verbose_name='邮箱')
    password = models.CharField(max_length=100, verbose_name='密码')
    # 修改密码时保存的临时密码
    temp_password = models.CharField(max_length=100, default=None, null=True, verbose_name='修改密码时保存的临时密码')
    # 是否激活
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    # 验证码
    code = models.CharField(max_length=6, verbose_name='验证码')
    # 可用总数
    valid_count = models.IntegerField(default=0, verbose_name='可用下载数')
    # 已用总数
    used_count = models.IntegerField(default=0, verbose_name='已用下载数')
    # 防止统一账号同时下载多个资源
    is_downloading = models.BooleanField(default=False, verbose_name='是否正在下载')

    class Meta:
        db_table = 'user'


class Service(Base):
    total_amount = models.FloatField(verbose_name='总金额')
    purchase_count = models.IntegerField(verbose_name='下载次数')

    class Meta:
        db_table = 'service'


class Resource(Base):
    # 资源地址，如果是上传资源，则留空
    url = models.CharField(max_length=200, null=True, default=None, verbose_name='资源地址')
    title = models.CharField(max_length=100, verbose_name='资源标题')
    filename = models.CharField(max_length=100, verbose_name='资源文件名')
    desc = models.TextField(null=True, default=None, verbose_name='资源描述')
    size = models.IntegerField(verbose_name='资源文件大小')
    category = models.CharField(max_length=100, null=True, verbose_name='资源分类')
    # 存储在oss中的key
    key = models.CharField(max_length=200, verbose_name='资源存储文件')
    # 以 !sep! 分离
    tags = models.CharField(max_length=240, verbose_name='资源标签')
    # 下载次数
    download_count = models.IntegerField(default=1)
    # 上传资源的用户
    user = models.ForeignKey(User, null=True, default=None, on_delete=models.DO_NOTHING)
    # 是否通过审核 1审核通过 0正在审核 -1已删除
    is_audited = models.SmallIntegerField(default=1, verbose_name='是否通过审核')
    # 文件的md5值
    file_md5 = models.CharField(max_length=100)

    class Meta:
        db_table = 'resource'


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 资源地址
    resource_url = models.CharField(max_length=200, null=True, verbose_name='资源地址')
    resource = models.ForeignKey(Resource, null=True, default=None, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name='是否被删除')
    title = models.CharField(max_length=100, verbose_name='资源名称')
    account = models.EmailField(null=True, default=None, verbose_name='使用的会员账号')

    class Meta:
        db_table = 'download_record'


class Coupon(Base):
    """
    优惠券
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.FloatField(verbose_name='总金额')
    purchase_count = models.IntegerField(verbose_name='下载次数')
    is_used = models.BooleanField(default=False, verbose_name='是否使用')
    # 优惠券唯一编码
    code = models.CharField(max_length=50, verbose_name='优惠券唯一编码')
    comment = models.CharField(max_length=100, null=True, verbose_name='备注')

    class Meta:
        db_table = 'coupon'


class Order(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 订单名称
    subject = models.CharField(max_length=50, verbose_name='订单名称')
    # 唯一订单号
    out_trade_no = models.CharField(max_length=50, unique=True, verbose_name='订单号')
    # 总金额
    total_amount = models.FloatField(verbose_name='总金额')
    # 支付时间
    paid_time = models.DateTimeField(null=True, verbose_name='支付时间')
    pay_url = models.TextField(verbose_name='支付地址')
    # 购买次数
    purchase_count = models.IntegerField(verbose_name='下载次数')
    coupon = models.OneToOneField(Coupon, on_delete=models.DO_NOTHING, null=True)

    class Meta:
        db_table = 'order'


class CsdnAccount(Base):
    github_username = models.CharField(max_length=50, verbose_name='账号绑定的GitHub用户名')
    github_password = models.CharField(max_length=50, verbose_name='账号绑定的GitHub密码')
    username = models.CharField(max_length=50, verbose_name='账号唯一名称')
    phone = models.CharField(max_length=20, verbose_name='账号绑定手机号')
    email = models.EmailField(verbose_name='联系邮箱')
    cookies = models.TextField(null=True, default=None)
    used_count = models.IntegerField(default=0, verbose_name='使用下载数')
    is_enabled = models.BooleanField(default=True, verbose_name='是否使用该账号')

    class Meta:
        db_table = 'csdn_account'


class BaiduAccount(Base):
    username = models.CharField(max_length=50, verbose_name='账号登录名')
    password = models.CharField(max_length=50, verbose_name='账号密码')
    nickname = models.CharField(max_length=50, verbose_name='账号唯一昵称')
    email = models.EmailField(verbose_name='联系邮箱')
    cookies = models.TextField(null=True, default=None)
    used_count = models.IntegerField(default=0, verbose_name='使用下载数')
    is_enabled = models.BooleanField(default=True, verbose_name='是否使用该账号')

    class Meta:
        db_table = 'baidu_account'


