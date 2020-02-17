# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import user, service, download, pay, resource, advert

urlpatterns = [
    path('login/', user.login),
    path('register/', user.register),
    re_path(r'^activate/?$', user.activate),
    path('reset_password/', user.reset_password),
    re_path(r'^forget_password/?$', user.forget_password),
    re_path(r'^reset_email/?$', user.send_forget_password_email),
    re_path(r'^wx/?$', user.wx),
    path('change_nickname/', user.change_nickname),
    path('get_user/', user.get_user),

    path('service/', service.list_services),
    path('list_orders/', service.list_orders),
    path('create_order/', service.create_order),
    path('alipay_notify/', pay.alipay_notify),
    path('list_coupons/', service.list_coupons),
    re_path(r'^delete_order/?$', service.delete_order),

    re_path(r'^refresh_baidu_cookies/?$', download.refresh_baidu_cookies),
    re_path(r'^refresh_csdn_cookies/?$', download.refresh_csdn_cookies),
    path('resource_tags/', download.resource_tags),
    path('list_download_records/', download.list_download_records),
    re_path(r'^delete_download_record/?$', download.delete_download_record),
    re_path(r'^list_resources/?$', download.list_resources),
    path('resource_count/', download.resource_count),
    path('oss_download/', download.oss_download),
    path('download/', download.download),
    path('upload/', resource.upload),
    re_path(r'^check_file/?$', resource.check_file),
    path('uploaded_resources/', resource.list_uploaded_resources),
    re_path(r'^get_resource/?$', resource.get_resource_by_id),
    re_path(r'^list_comments/?$', resource.list_comments),
    path('create_comment/', resource.create_comment),
    re_path(r'^related_resources/?$', resource.list_related_resources),

    re_path(r'^get_random_advert/?$', advert.get_random_advert)
]
