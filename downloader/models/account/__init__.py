from downloader.models.account.deprecated import *

ACCOUNT_TYPE_CSDN = 0  # https://download.csdn.net/
ACCOUNT_TYPE_WENKU = 1  # https://wenku.baidu.com/
ACCOUNT_TYPE_DOCER = 2  # https://www.docer.com/
ACCOUNT_TYPE_MBZJ = 3  # http://www.cssmoban.com/
ACCOUNT_TYPE_QIANTU = 4  # https://www.58pic.com/

STATUS_DISABLED = 0
STATUS_ENABLED = 1
STATUS_EXPIRED = 2


class DownloadAccount(Base):
    type = models.IntegerField(verbose_name="账号类型")
    config = models.TextField(verbose_name="账号配置")
    status = models.IntegerField(verbose_name="账号状态")

    class Meta:
        db_table = "download_account"
