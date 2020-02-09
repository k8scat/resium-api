# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import user, service, download, pay

urlpatterns = [
    path('login/', user.login),
    path('register/', user.register),
    re_path(r'^activate/?$', user.activate),
    path('reset_password/', user.reset_password),
    re_path(r'^forget_password/?$', user.forget_password),
    re_path(r'^reset_email/?$', user.send_forget_password_email),
    re_path(r'^wx/?$', user.wx),

    path('service/', service.list_services),
    path('order/', service.list_orders),
    path('create_order/', service.create_order),
    path('alipay_notify/', pay.alipay_notify),
    path('coupon/', service.list_coupons),

    re_path(r'^refresh_baidu_cookies/?$', download.refresh_baidu_cookies),
    re_path(r'^refresh_csdn_cookies/?$', download.refresh_csdn_cookies),
    path('resource_tags/', download.resource_tags),
    path('download_record/', download.download_record),
    re_path(r'^resource/?$', download.resource),
    path('resource_count/', download.resource_count),
    path('resource_download/', download.oss_download),
    path('download/', download.download),
]
