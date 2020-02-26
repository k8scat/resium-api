# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import user, service, order, resource, advert, coupon, account, download_record

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

    path('list_orders/', order.list_orders),
    path('create_order/', order.create_order),
    path('alipay_notify/', order.alipay_notify),
    re_path(r'^delete_order/?$', order.delete_order),

    path('list_coupons/', coupon.list_coupons),

    re_path(r'^refresh_baidu_cookies/?$', account.refresh_baidu_cookies),
    re_path(r'^refresh_csdn_cookies/?$', account.refresh_csdn_cookies),

    path('list_download_records/', download_record.list_download_records),
    re_path(r'^delete_download_record/?$', download_record.delete_download_record),

    path('oss_download/', resource.oss_download),
    path('download/', resource.download),
    path('upload/', resource.upload),
    re_path(r'^check_file/?$', resource.check_file),
    path('uploaded_resources/', resource.list_uploaded_resources),
    re_path(r'^get_resource/?$', resource.get_resource),
    re_path(r'^list_comments/?$', resource.list_comments),
    path('create_comment/', resource.create_comment),
    re_path(r'^related_resources/?$', resource.list_related_resources),
    path('list_resource_tags/', resource.list_resource_tags),
    re_path(r'^list_resources/?$', resource.list_resources),
    path('get_resource_count/', resource.get_resource_count),

    re_path(r'^get_random_advert/?$', advert.get_random_advert),
]
