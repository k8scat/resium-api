from django.db import models

from downloader.models import Base


class Service(Base):
    total_amount = models.FloatField(verbose_name="总金额")
    point = models.IntegerField(verbose_name="下载积分")
    is_hot = models.BooleanField(default=False, verbose_name="活动")

    class Meta:
        db_table = "service"
