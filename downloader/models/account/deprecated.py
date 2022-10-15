from django.db import models

from downloader.models import Base
from downloader.models.user import User


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
