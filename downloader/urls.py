# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import login, register, activate, order, notify, download, get_user, reset_password, \
    download_record

urlpatterns = [
    path('login/', login),
    path('register/', register),
    re_path(r'^activate/?$', activate),
    re_path(r'^order/?$', order),
    path('notify/', notify),
    path('download/', download),
    path('user/', get_user),
    path('reset_password/', reset_password),
    path('download_record/',  download_record),
]
