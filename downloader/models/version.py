from django.db import models

from downloader.models import Base


class Version(Base):
    version = models.CharField(max_length=50, verbose_name="版本号")

    class Meta:
        db_table = "version"
