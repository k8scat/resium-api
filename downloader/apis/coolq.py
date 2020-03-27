# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

CoolQ API

"""
import hmac
import logging

from django.conf import settings
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request


@api_view(['POST'])
def receive(request: Request):
    if request.method == 'POST':
        logging.info(request.headers)
        x_sig = request.headers.get('X-Signature', None)
        qq = request.headers.get('X-Self-ID', None)
        if x_sig and qq == settings.CQ_QQ:
            sig = hmac.new(settings.CQ_SECRET, request.body, 'sha1').hexdigest()
            received_sig = x_sig[len('sha1='):]
            if sig == received_sig:
                logging.info('ok')
                # 请求确实来自于插件
                logging.info(request.data)
        return HttpResponse(status=204)
