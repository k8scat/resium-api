# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import *

urlpatterns = [
    path('login/', login),
    path('register/', register),
    re_path(r'^activate/?$', activate),
    re_path(r'^order/?$', order),
    path('alipay_notify/', alipay_notify),
    path('download/', download),
    path('user/', get_user),
    path('reset_password/', reset_password),
    path('download_record/', download_record),
    path('service/', service),
    path('status/', get_status),
    path('test/', test),
    re_path(r'^resource/?$', resource),
    path('resource_count/', resource_count),
    path('resource_download/', resource_download),
    path('coupon/', coupon),
]
