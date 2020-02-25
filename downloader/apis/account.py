# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
from threading import Thread

from django.conf import settings
from django.http import HttpResponse
from rest_framework.decorators import api_view

from downloader.utils import csdn_auto_login, baidu_auto_login


@api_view(['GET'])
def refresh_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', None)
        if token == settings.ADMIN_TOKEN:
            t = Thread(target=csdn_auto_login)
            t.start()
        return HttpResponse('')


@api_view(['GET'])
def refresh_baidu_cookies(request):
    """
    更新百度 cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', '')
        if token == settings.ADMIN_TOKEN:
            t = Thread(target=baidu_auto_login)
            t.start()
        return HttpResponse('')
