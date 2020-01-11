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
    path('download_record/',  download_record),
    path('service/', service),
    path('test/', test),
    path('today_download_count/', get_today_download_count),
    path('user_count/', get_user_count),
    path('status/', get_status)
]
