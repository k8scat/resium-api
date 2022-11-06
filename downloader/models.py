from django.db import models


class Base(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        abstract = True


class User(Base):
    uid = models.CharField(max_length=100, unique=True, verbose_name="用户的唯一标识")
    password = models.CharField(
        max_length=100, default=None, null=True, verbose_name="登录密码"
    )
    nickname = models.CharField(max_length=100, default=None, verbose_name="昵称")
    avatar_url = models.CharField(max_length=240, verbose_name="头像地址")
    point = models.IntegerField(default=0, verbose_name="下载积分")
    used_point = models.IntegerField(default=0, verbose_name="已使用积分")
    login_time = models.DateTimeField(null=True, default=None, verbose_name="登录时间")
    can_download = models.BooleanField(default=False, verbose_name="是否可以下载其他站点的资源")
    can_upload = models.BooleanField(default=True, verbose_name="是否可以上传资源")
    wx_openid = models.CharField(
        max_length=100, default=None, null=True, verbose_name="微信公众号用户唯一标识"
    )
    is_admin = models.BooleanField(default=False, verbose_name="管理员账号")
    mp_openid = models.CharField(
        max_length=100, default=None, null=True, verbose_name="小程序用户唯一标识"
    )
    email = models.EmailField(verbose_name="邮箱", default=None, null=True)
    code = models.CharField(
        max_length=200,
        unique=True,
        default=None,
        null=True,
        verbose_name="用来验证用户可靠性，新账号和旧账号替换",
    )
    gender = models.SmallIntegerField(null=True, default=None, verbose_name="性别")

    class Meta:
        db_table = "user"


class Resource(Base):
    # 资源地址，如果是上传资源，则留空
    # 资源地址可能相同，知网的同一个地址可以下载pdf或者caj
    url = models.CharField(max_length=200, null=True, default=None, verbose_name="资源地址")
    title = models.CharField(max_length=200, verbose_name="资源标题")
    filename = models.TextField(null=True, default=None, verbose_name="资源文件名")
    desc = models.TextField(null=True, default=None, verbose_name="资源描述")
    size = models.IntegerField(verbose_name="资源文件大小")
    # 存储在oss中的key，默认为空
    key = models.CharField(
        max_length=200, null=True, default=None, verbose_name="资源存储文件"
    )
    # 以 !sep! 分离
    tags = models.TextField(null=True, default=None, verbose_name="资源标签")
    # 下载次数
    download_count = models.IntegerField(default=1)
    # 上传资源的用户
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    # 是否通过审核 1审核通过 0正在审核 -1已删除
    is_audited = models.SmallIntegerField(default=1, verbose_name="是否通过审核")
    file_md5 = models.CharField(max_length=100, verbose_name="文件的md5值")

    class Meta:
        db_table = "resource"


class CheckInRecord(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    point = models.SmallIntegerField(verbose_name="签到获得的积分")

    class Meta:
        db_table = "check_in_record"


class QrCode(Base):
    cid = models.CharField(max_length=100, unique=True, verbose_name="二维码唯一标志")
    has_scanned = models.BooleanField(default=False, verbose_name="判断是否使用小程序扫码")
    code_type = models.CharField(max_length=20, verbose_name="二维码类型，bing或者login")
    uid = models.CharField(
        max_length=50, default=None, null=True, verbose_name="扫码登录时保存的uid"
    )

    class Meta:
        db_table = "qr_code"


class PointRecord(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    point = models.IntegerField(verbose_name="剩余积分")
    used_point = models.IntegerField(default=0, verbose_name="使用积分")
    add_point = models.IntegerField(default=0, verbose_name="增加积分")
    comment = models.CharField(max_length=100, verbose_name="积分使用备注")
    url = models.CharField(max_length=240, default=None, null=True, verbose_name="链接")
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "point_record"


class ResourceComment(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        db_table = "resource_comment"


class DocerPreviewImage(Base):
    """
    稻壳模板预览图片
    """

    resource_url = models.CharField(max_length=240, verbose_name="资源地址")
    url = models.CharField(max_length=240, verbose_name="图片地址")
    alt = models.TextField(verbose_name="图片解释")

    class Meta:
        db_table = "docer_preview_image"


class DocConvertRecord(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    download_url = models.CharField(
        max_length=240, default=None, null=True, verbose_name="转换成功后的下载链接"
    )
    point = models.IntegerField(default=0)

    class Meta:
        db_table = "doc_convert_record"


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name="是否被用户删除")
    used_point = models.IntegerField(default=0, verbose_name="下载使用的积分")
    # null的时候表示直接从oss中下载的
    account_id = models.IntegerField(default=None, null=True)

    class Meta:
        db_table = "download_record"


class Article(Base):
    user = models.ForeignKey(User, null=True, default=None, on_delete=models.DO_NOTHING)
    url = models.CharField(
        max_length=200, null=True, default=None, verbose_name="文章链接", unique=True
    )
    title = models.CharField(max_length=200, verbose_name="文章标题")
    content = models.TextField(verbose_name="文章内容")
    author = models.CharField(max_length=100, verbose_name="文章作者")
    is_vip = models.BooleanField(default=False, verbose_name="VIP文章")
    desc = models.TextField(verbose_name="文章简介")
    tags = models.CharField(max_length=200, verbose_name="文章标签")  # deprecated
    view_count = models.IntegerField(default=0)
    is_original = models.BooleanField(default=False, verbose_name="原创")

    class Meta:
        db_table = "article"


class ArticleComment(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        db_table = "article_comment"


class CsdnAccount(Base):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    cookies = models.TextField(null=True, default=None)
    used_count = models.IntegerField(default=0, verbose_name="使用下载数")
    valid_count = models.IntegerField(default=0, verbose_name="可用下载数")
    today_download_count = models.IntegerField(default=0, verbose_name="今日已下载数")
    is_enabled = models.BooleanField(default=False, verbose_name="是否使用该账号")
    is_cookies_valid = models.BooleanField(default=True, verbose_name="Cookies是否有效")
    need_sms_validate = models.BooleanField(default=False, verbose_name="是否需要短信验证")
    is_disabled = models.BooleanField(default=False, verbose_name="是否被禁用")
    csdn_id = models.IntegerField(verbose_name="CSDN ID")
    qq = models.CharField(max_length=20, verbose_name="账号拥有者的QQ号")
    unit_price = models.FloatField(default=None, null=True, verbose_name="下载单价")

    class Meta:
        db_table = "csdn_account"


class BaiduAccount(Base):
    email = models.EmailField(verbose_name="联系邮箱")
    cookies = models.TextField(null=True, default=None)
    is_enabled = models.BooleanField(default=False, verbose_name="是否使用该账号")
    vip_free_count = models.IntegerField(default=0, verbose_name="VIP免费文档使用数")
    share_doc_count = models.IntegerField(default=0, verbose_name="共享文档使用数")
    special_doc_count = models.IntegerField(default=0, verbose_name="VIP专享文档使用数")

    class Meta:
        db_table = "baidu_account"


class DocerAccount(Base):
    cookies = models.TextField(null=True, default=None)
    email = models.EmailField(verbose_name="联系邮箱")
    used_count = models.IntegerField(default=0, verbose_name="使用下载数")
    is_enabled = models.BooleanField(default=False, verbose_name="是否使用该账号")
    # todo: 定时任务：每月更新下载数
    month_used_count = models.IntegerField(default=0, verbose_name="当月已使用VIP下载数")

    class Meta:
        db_table = "docer_account"


class MbzjAccount(Base):
    """
    http://www.cssmoban.com/
    """

    is_enabled = models.BooleanField(default=False)
    user_id = models.CharField(max_length=20, verbose_name="账号ID")
    secret_key = models.CharField(max_length=100, verbose_name="用于请求接口")

    class Meta:
        db_table = "mbzj_account"


class TaobaoWenkuAccount(Base):
    account = models.CharField(max_length=50, verbose_name="账号")
    password = models.CharField(max_length=50, verbose_name="密码")
    is_enabled = models.BooleanField(default=True, verbose_name="是否使用该账号")

    class Meta:
        db_table = "taobao_wenku_account"


class QiantuAccount(Base):
    cookies = models.TextField(null=True, default=None)
    email = models.EmailField(verbose_name="账号拥有者的联系邮箱")
    used_count = models.IntegerField(default=0, verbose_name="使用下载数")
    is_enabled = models.BooleanField(default=False, verbose_name="是否使用该账号")

    class Meta:
        db_table = "qiantu_account"


DOWNLOAD_ACCOUNT_TYPE_CSDN = 0  # https://download.csdn.net/
DOWNLOAD_ACCOUNT_TYPE_WENKU = 1  # https://wenku.baidu.com/
DOWNLOAD_ACCOUNT_TYPE_DOCER = 2  # https://www.docer.com/
DOWNLOAD_ACCOUNT_TYPE_MBZJ = 3  # http://www.cssmoban.com/
DOWNLOAD_ACCOUNT_TYPE_QIANTU = 4  # https://www.58pic.com/

DOWNLOAD_ACCOUNT_STATUS_DISABLED = 0
DOWNLOAD_ACCOUNT_STATUS_ENABLED = 1
DOWNLOAD_ACCOUNT_STATUS_EXPIRED = 2


class DownloadAccount(Base):
    type = models.IntegerField(verbose_name="账号类型")
    config = models.TextField(verbose_name="账号配置")
    status = models.IntegerField(verbose_name="账号状态")

    class Meta:
        db_table = "download_account"


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


class Service(Base):
    total_amount = models.FloatField(verbose_name="总金额")
    point = models.IntegerField(verbose_name="下载积分")
    is_hot = models.BooleanField(default=False, verbose_name="活动")

    class Meta:
        db_table = "service"


class Version(Base):
    version = models.CharField(max_length=50, verbose_name="版本号")

    class Meta:
        db_table = "version"


class UploadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name="是否被用户删除")

    class Meta:
        db_table = "upload_record"


class Advert(Base):
    link = models.CharField(max_length=240, verbose_name="推广链接")
    image = models.CharField(max_length=240, verbose_name="推广图片")
    title = models.CharField(max_length=100, verbose_name="推广标题")

    class Meta:
        db_table = "advert"


class MpSwiperAd(Base):
    """
    小程序轮播图广告

    """

    title = models.CharField(max_length=100, verbose_name="Modal的标题")
    content = models.CharField(max_length=100, verbose_name="Modal的内容")
    image_url = models.CharField(max_length=200, verbose_name="swiper的图片")
    clipboard_data = models.CharField(max_length=100, verbose_name="复制到剪切板的内容")
    msg = models.CharField(max_length=100, verbose_name="复制成功的消息")
    is_ok = models.BooleanField(default=True, verbose_name="是否展示")

    class Meta:
        db_table = "mp_swiper_ad"


class Notice(Base):
    """
    小程序公告
    """

    title = models.CharField(max_length=100, verbose_name="公告标题")
    content = models.CharField(max_length=240, verbose_name="公告内容")

    class Meta:
        db_table = "notice"
