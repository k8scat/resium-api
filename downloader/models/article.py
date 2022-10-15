from django.db import models

from downloader.models import Base
from downloader.models.user import User


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
    tags = models.CharField(max_length=200, verbose_name="文章标签")
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
