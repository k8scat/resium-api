from django.conf import settings
from django.contrib import admin
from downloader.models import *

# 参考: https://blog.csdn.net/longdreams/article/details/78475582


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'email', 'valid_count', 'used_count', 'create_time', 'update_time')
    list_per_page = 50
    search_fields = ['email']


@admin.register(DownloadRecord)
class DownloadRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'create_time', 'is_deleted')
    list_filter = ('is_deleted',)
    search_fields = ['title']
    list_per_page = 50


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'purchase_count', 'total_amount', 'paid_time', 'create_time')
    list_filter = ('purchase_count',)
    list_per_page = 50


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('total_amount', 'purchase_count', 'create_time', 'update_time')
    list_filter = ('create_time', 'update_time', 'total_amount', 'purchase_count')


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'key', 'create_time')
    list_per_page = 50
    search_fields = ['title']


@admin.register(Csdnbot)
class CsdnbotAdmin(admin.ModelAdmin):
    list_display = ('status', 'update_time')


admin.site.site_header = 'CSDNBot Admin'
admin.site.site_title = 'CSDNBot Admin'
admin.site.site_url = settings.CSDNBOT_UI
