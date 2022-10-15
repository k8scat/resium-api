from django.db import models

from downloader.models import Base
from downloader.models.user import User


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

    wenku_type = models.CharField(
        max_length=100, null=True, default=None, verbose_name="百度文库文档类型"
    )
    is_docer_vip_doc = models.BooleanField(default=False, verbose_name="是否是稻壳VIP文档")

    local_path = models.CharField(
        max_length=200, default=None, null=True, verbose_name="资源本地保存路径"
    )

    class Meta:
        db_table = "resource"


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
