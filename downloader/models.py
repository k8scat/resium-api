from django.db import models


class Base(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        abstract = True


class User(Base):
    uid = models.CharField(max_length=100, unique=True, verbose_name='用户的唯一标识')
    nickname = models.CharField(max_length=100, default=None, verbose_name='昵称')
    avatar_url = models.CharField(max_length=240, verbose_name='头像地址')
    point = models.IntegerField(default=0, verbose_name='下载积分')
    used_point = models.IntegerField(default=0, verbose_name='已使用积分')
    login_time = models.DateTimeField(null=True, default=None, verbose_name='登录时间')
    can_download = models.BooleanField(default=False, verbose_name='是否可以下载其他站点的资源')
    qq_openid = models.CharField(max_length=100, unique=True, default=None, null=True, verbose_name='QQ唯一标识')
    has_check_in_today = models.BooleanField(default=False, verbose_name='今日是否签到')
    wx_openid = models.CharField(max_length=100, default=None, null=True, verbose_name='微信公众号用户唯一标识')
    github_id = models.IntegerField(default=None, null=True)
    gitee_id = models.IntegerField(default=None, null=True)
    baidu_openid = models.CharField(max_length=100, default=None, null=True)
    dingtalk_openid = models.CharField(max_length=100, default=None, null=True)
    coding_user_id = models.IntegerField(default=None, null=True)
    is_admin = models.BooleanField(default=False, verbose_name='是否是管理员账号')
    mp_openid = models.CharField(max_length=100, default=None, null=True, verbose_name='小程序用户唯一标识')

    # 废弃的字段
    email = models.EmailField(verbose_name='邮箱', default=None, null=True)
    code = models.CharField(max_length=200, unique=True, default=None, null=True, verbose_name='用来验证用户可靠性，新账号和旧账号替换')

    class Meta:
        db_table = 'user'


class Service(Base):
    total_amount = models.FloatField(verbose_name='总金额')
    point = models.IntegerField(verbose_name='下载积分')

    class Meta:
        db_table = 'service'


class Resource(Base):
    # 资源地址，如果是上传资源，则留空
    # 资源地址可能相同，知网的同一个地址可以下载pdf或者caj
    url = models.CharField(max_length=200, null=True, default=None, verbose_name='资源地址')
    title = models.CharField(max_length=100, verbose_name='资源标题')
    filename = models.CharField(max_length=100, null=True, default=None, verbose_name='资源文件名')
    desc = models.TextField(null=True, default=None, verbose_name='资源描述')
    size = models.IntegerField(verbose_name='资源文件大小')
    # 存储在oss中的key，默认为空
    key = models.CharField(max_length=200, null=True, default=None, verbose_name='资源存储文件')
    # 以 !sep! 分离
    tags = models.CharField(null=True, default=None, max_length=240, verbose_name='资源标签')
    # 下载次数
    download_count = models.IntegerField(default=1)
    # 上传资源的用户
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    # 是否通过审核 1审核通过 0正在审核 -1已删除
    is_audited = models.SmallIntegerField(default=1, verbose_name='是否通过审核')
    file_md5 = models.CharField(max_length=100, verbose_name='文件的md5值')
    wenku_type = models.CharField(max_length=100, null=True, default=None, verbose_name='百度文库文档类型')
    is_docer_vip_doc = models.BooleanField(default=False, verbose_name='是否是稻壳VIP文档')
    local_path = models.CharField(max_length=200, default=None, null=True, verbose_name='资源本地保存路径')

    class Meta:
        db_table = 'resource'


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, null=True, default=None, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name='是否被删除')
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
    is_enabled = models.BooleanField(default=False, verbose_name='是否使用该账号')
    need_sms_validate = models.BooleanField(default=False, verbose_name='是否需要短信验证')

    class Meta:
        db_table = 'csdn_account'


class BaiduAccount(Base):
    email = models.EmailField(verbose_name='联系邮箱')
    cookies = models.TextField(null=True, default=None)
    is_enabled = models.BooleanField(default=False, verbose_name='是否使用该账号')
    vip_free_count = models.IntegerField(default=0, verbose_name='VIP免费文档使用数')
    share_doc_count = models.IntegerField(default=0, verbose_name='共享文档使用数')
    special_doc_count = models.IntegerField(default=0, verbose_name='VIP专享文档使用数')

    class Meta:
        db_table = 'baidu_account'


class DocerAccount(Base):
    cookies = models.TextField(null=True, default=None)
    email = models.EmailField(verbose_name='联系邮箱')
    used_count = models.IntegerField(default=0, verbose_name='使用下载数')
    is_enabled = models.BooleanField(default=False, verbose_name='是否使用该账号')
    # todo: 定时任务：每月更新下载数
    month_used_count = models.IntegerField(default=0, verbose_name='当月已使用VIP下载数')

    class Meta:
        db_table = 'docer_account'


class QiantuAccount(Base):
    cookies = models.TextField(null=True, default=None)
    email = models.EmailField(verbose_name='账号拥有者的联系邮箱')
    used_count = models.IntegerField(default=0, verbose_name='使用下载数')
    is_enabled = models.BooleanField(default=False, verbose_name='是否使用该账号')

    class Meta:
        db_table = 'qiantu_account'


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


class Article(Base):
    user = models.ForeignKey(User, null=True, default=None, on_delete=models.DO_NOTHING)
    url = models.CharField(max_length=200, null=True, default=None, verbose_name='文章链接', unique=True)
    title = models.CharField(max_length=200, verbose_name='文章标题')
    content = models.TextField(verbose_name='文章内容')
    author = models.CharField(max_length=100, verbose_name='文章作者')
    is_vip = models.BooleanField(default=False, verbose_name='VIP文章')
    desc = models.CharField(max_length=240, verbose_name='文章简介')
    tags = models.CharField(max_length=200, verbose_name='文章标签')
    view_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'article'


class DocerPreviewImage(Base):
    """
    稻壳模板预览图片
    """

    resource_url = models.CharField(max_length=240, verbose_name='资源地址')
    url = models.CharField(max_length=240, verbose_name='图片地址')
    alt = models.CharField(max_length=200, verbose_name='图片解释')

    class Meta:
        db_table = 'docer_preview_image'


class TaobaoWenkuAccount(Base):
    account = models.CharField(max_length=50, verbose_name='账号')
    password = models.CharField(max_length=50, verbose_name='密码')
    is_enabled = models.BooleanField(default=True, verbose_name='是否使用该账号')

    class Meta:
        db_table = 'taobao_wenku_account'


class DwzRecord(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    url = models.CharField(max_length=240, verbose_name='原网址')
    generated_url = models.CharField(max_length=240, verbose_name='生成的网址')

    class Meta:
        db_table = 'dwz_record'


class CheckInRecord(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    point = models.SmallIntegerField(verbose_name='签到获得的积分')

    class Meta:
        db_table = 'check_in_record'


class DocConvertRecord(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    download_url = models.CharField(max_length=240, default=None, null=True, verbose_name='转换成功后的下载链接')
    point = models.IntegerField(default=0)

    class Meta:
        db_table = 'doc_convert_record'


class QrCode(Base):
    cid = models.CharField(max_length=100, unique=True, verbose_name='二维码唯一标志')
    has_scanned = models.BooleanField(default=False, verbose_name='判断是否使用小程序扫码')
    code_type = models.CharField(max_length=20, verbose_name='二维码类型，bing或者login')
    uid = models.CharField(max_length=50, default=None, null=True, verbose_name='扫码登录时保存的uid')

    class Meta:
        db_table = 'qr_code'


class FreeDownloadCode(Base):
    code = models.CharField(max_length=20)
    is_used = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'free_download_code'
