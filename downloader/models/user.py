from django.db import models

from downloader.models import Base
from downloader.models.resource import Resource


class User(Base):
    uid = models.CharField(max_length=100, unique=True, verbose_name="用户的唯一标识")
    password = models.CharField(
        max_length=100, default=None, null=True, verbose_name="H5登录密码"
    )
    nickname = models.CharField(max_length=100, default=None, verbose_name="昵称")
    avatar_url = models.CharField(max_length=240, verbose_name="头像地址")
    point = models.IntegerField(default=0, verbose_name="下载积分")
    used_point = models.IntegerField(default=0, verbose_name="已使用积分")
    login_time = models.DateTimeField(null=True, default=None, verbose_name="登录时间")
    can_download = models.BooleanField(default=False, verbose_name="是否可以下载其他站点的资源")
    can_upload = models.BooleanField(default=True, verbose_name="是否可以上传资源")
    has_check_in_today = models.BooleanField(default=False, verbose_name="今日是否签到")
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
    is_pattern = models.BooleanField(default=False, verbose_name="合作用户")
    gender = models.SmallIntegerField(null=True, default=None, verbose_name="性别")
    from_taobao = models.BooleanField(default=False, verbose_name="是否来自淘宝")

    class Meta:
        db_table = "user"


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
    resource = models.ForeignKey(
        Resource, default=None, null=True, on_delete=models.DO_NOTHING
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "point_record"
