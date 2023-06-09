from django.conf import settings
from django.contrib import admin
from downloader.models import *

# 参考: https://blog.csdn.net/longdreams/article/details/78475582


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "point", "used_point", "login_time")
    list_per_page = 50
    search_fields = ["uid", "nickname"]


@admin.register(DownloadRecord)
class DownloadRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "resource", "create_time")
    list_per_page = 50


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "has_paid",
        "user",
        "subject",
        "point",
        "total_amount",
        "create_time",
    )
    list_filter = ("has_paid",)
    list_per_page = 50


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "total_amount", "point", "create_time", "update_time")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "is_audited",
        "user",
        "title",
        "url",
        "key",
        "filename",
        "tags",
        "create_time",
    )
    list_per_page = 50
    list_filter = ("is_audited",)
    search_fields = ["title", "key", "url"]


@admin.register(Advert)
class AdvertAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "link", "image")
    list_per_page = 50
    search_fields = ["title"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "url")
    list_per_page = 50
    search_fields = ["title", "url", "author"]


admin.site.site_header = "源自下载后台"
admin.site.site_title = "源自下载后台"
admin.site.site_url = settings.FRONTEND_URL
