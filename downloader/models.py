from django.db import models


class Base(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        abstract = True


class User(Base):
    nickname = models.CharField(max_length=100, default=None, verbose_name='昵称')
    email = models.EmailField(verbose_name='邮箱')
    phone = models.CharField(max_length=20, null=True, default=None, verbose_name='手机号')
    password = models.CharField(max_length=100, verbose_name='密码')
    temp_password = models.CharField(max_length=100, default=None, null=True, verbose_name='修改密码时保存的临时密码')
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    code = models.CharField(max_length=6, verbose_name='验证码')
    point = models.IntegerField(default=0, verbose_name='下载积分')
    used_point = models.IntegerField(default=0, verbose_name='已使用积分')
    # 防止统一账号同时下载多个资源
    is_downloading = models.BooleanField(default=False, verbose_name='是否正在下载')
    login_device = models.TextField(null=True, default=None, verbose_name='登录设备')
    login_ip = models.CharField(max_length=100, null=True, default=None, verbose_name='登录IP')
    login_time = models.DateTimeField(null=True, default=None, verbose_name='登录时间')

    class Meta:
        db_table = 'user'


class Service(Base):
    total_amount = models.FloatField(verbose_name='总金额')
    point = models.IntegerField(verbose_name='下载积分')

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
    file_md5 = models.CharField(max_length=100, verbose_name='文件的md5值')
    wenku_type = models.CharField(max_length=100, null=True, default=None, verbose_name='百度文库文档类型')
    zhiwang_type = models.CharField(max_length=10, null=True, default=None, verbose_name='知网文献类型(caj/pdf)')

    class Meta:
        db_table = 'resource'


class Tag(Base):
    name = models.CharField(max_length=100, verbose_name='标签名称')
    resource = models.ForeignKey(Resource, on_delete=models.DO_NOTHING)


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, null=True, default=None, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name='是否被删除')
    download_device = models.CharField(max_length=200, null=True, default=None, verbose_name='下载资源时使用的设备')
    download_ip = models.CharField(max_length=100, null=True, default=None, verbose_name='下载资源时的ip地址')
    used_point = models.IntegerField(default=0, verbose_name='下载使用的积分')
    account = models.EmailField(null=True, default=None, verbose_name='使用的会员账号')

    class Meta:
        db_table = 'download_record'


class Coupon(Base):
    """
    优惠券
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.FloatField(verbose_name='总金额')
    point = models.IntegerField(verbose_name='下载积分')
    is_used = models.BooleanField(default=False, verbose_name='是否使用')
    code = models.CharField(max_length=50, verbose_name='优惠券唯一编码')
    comment = models.CharField(max_length=100, null=True, verbose_name='备注')

    class Meta:
        db_table = 'coupon'


class Order(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=50, verbose_name='订单名称')
    out_trade_no = models.CharField(max_length=50, unique=True, verbose_name='订单号')
    total_amount = models.FloatField(verbose_name='总金额')
    has_paid = models.BooleanField(default=False, verbose_name='是否支付')
    pay_url = models.TextField(verbose_name='支付地址')
    point = models.IntegerField(verbose_name='下载积分')
    coupon = models.OneToOneField(Coupon, on_delete=models.DO_NOTHING, null=True, verbose_name='使用的优惠券')
    is_deleted = models.BooleanField(default=False, verbose_name='是否被删除')

    class Meta:
        db_table = 'order'


class CsdnAccount(Base):
    email = models.EmailField(verbose_name='联系邮箱')
    cookies = models.TextField(null=True, default=None)
    used_count = models.IntegerField(default=0, verbose_name='使用下载数')
    today_download_count = models.IntegerField(default=0, verbose_name='今日已下载数')
    is_enabled = models.BooleanField(default=True, verbose_name='是否使用该账号')

    class Meta:
        db_table = 'csdn_account'


class BaiduAccount(Base):
    email = models.EmailField(verbose_name='联系邮箱')
    cookies = models.TextField(null=True, default=None)
    is_enabled = models.BooleanField(default=True, verbose_name='是否使用该账号')
    vip_free_count = models.IntegerField(default=0, verbose_name='VIP免费文档使用数')
    share_doc_count = models.IntegerField(default=0, verbose_name='共享文档使用数')
    special_doc_count = models.IntegerField(default=0, verbose_name='VIP专享文档使用数')

    class Meta:
        db_table = 'baidu_account'


class DocerAccount(Base):
    cookies = models.TextField(null=True, default=None)
    email = models.EmailField(verbose_name='联系邮箱')
    used_count = models.IntegerField(default=0, verbose_name='使用下载数')
    is_enabled = models.BooleanField(default=True, verbose_name='是否使用该账号')

    class Meta:
        db_table = 'docer_account'


class ResourceComment(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    content = models.CharField(max_length=240)

    class Meta:
        db_table = 'resource_comment'


class Advert(Base):
    link = models.CharField(max_length=240, verbose_name='推广链接')
    image = models.CharField(max_length=240, verbose_name='推广图片')
    title = models.CharField(max_length=100, verbose_name='推广标题')

    class Meta:
        db_table = 'advert'

