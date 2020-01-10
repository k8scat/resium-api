from django.contrib import admin
from downloader.models import *


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'valid_count', 'used_count', 'create_time', 'update_time')
    list_filter = ('create_time', 'email', 'valid_count', 'used_count')


class DownloadRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource_url', 'create_time')
    list_filter = ('create_time', 'user', 'resource_url')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'purchase_count', 'total_amount', 'paid_time', 'create_time')
    list_filter = ('create_time', 'paid_time', 'subject', 'user', 'total_amount', 'purchase_count')


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('total_amount', 'purchase_count', 'create_time', 'update_time')
    list_filter = ('create_time', 'update_time', 'total_amount', 'purchase_count')


admin.site.register(User, UserAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(DownloadRecord, DownloadRecordAdmin)
admin.site.register(Service, ServiceAdmin)
