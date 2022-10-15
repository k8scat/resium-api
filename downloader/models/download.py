from django.db import models

from downloader.models import Base
from downloader.models.resource import Resource
from downloader.models.user import User


class DownloadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name="是否被用户删除")
    used_point = models.IntegerField(default=0, verbose_name="下载使用的积分")
    # null的时候表示直接从oss中下载的
    account_id = models.IntegerField(default=None, null=True)

    class Meta:
        db_table = "download_record"
