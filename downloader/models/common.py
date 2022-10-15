from django.db import models

from downloader.models.base import Base


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
