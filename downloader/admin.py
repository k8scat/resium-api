from django.conf import settings
from django.contrib import admin
from downloader.models import *

# 参考: https://blog.csdn.net/longdreams/article/details/78475582


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'is_active', 'has_subscribed', 'valid_count', 'used_count', 'create_time', 'update_time')
    list_per_page = 50
    list_filter = ('has_subscribed', 'is_active')
    search_fields = ['email']


@admin.register(DownloadRecord)
class DownloadRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'create_time', 'is_deleted')
    list_filter = ('is_deleted',)
    search_fields = ['title']
    list_per_page = 50


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'purchase_count', 'total_amount', 'paid_time', 'create_time')
    list_filter = ('purchase_count',)
    list_per_page = 50


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'total_amount', 'purchase_count', 'create_time', 'update_time')


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'key', 'create_time')
    list_per_page = 50
    search_fields = ['title']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_used', 'total_amount', 'purchase_count', 'create_time')
    list_per_page = 50
    search_fields = ['title']
    list_filter = ('is_used',)


@admin.register(CsdnAccount)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone', 'github_username', 'username', 'used_count', 'update_time')
    list_per_page = 50
    search_fields = ['email', 'github_username', 'phone', 'username']


@admin.register(BaiduAccount)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'nickname', 'used_count', 'update_time')
    list_per_page = 50
    search_fields = ['email', 'nickname', 'username']


admin.site.site_header = 'CSDNBot Admin'
admin.site.site_title = 'CSDNBot Admin'
admin.site.site_url = settings.CSDNBOT_UI
