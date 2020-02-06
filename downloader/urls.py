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
    path('test/', test),
    re_path(r'^resource/?$', resource),
    path('resource_count/', resource_count),
    path('resource_download/', resource_download),
    path('coupon/', coupon),
    re_path(r'^refresh_cookies/?$', refresh_cookies),
    re_path(r'^wx/?$', wx),
    re_path(r'^check_wenku_cookies/?$', check_wenku_cookies),
    path('resource_tags/', resource_tags),
    re_path(r'^forget_password/?$', forget_password),
    re_path(r'^reset_email/?$', send_forget_password_email),
]
