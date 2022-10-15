from django.db import models

from downloader.models import Base
from downloader.models.resource import Resource
from downloader.models.user import User


class UploadRecord(Base):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False, verbose_name="是否被用户删除")

    class Meta:
        db_table = "upload_record"
