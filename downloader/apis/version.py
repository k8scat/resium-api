# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2021/10/22

"""
from urllib.parse import quote, unquote
import uuid
import json

import requests

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q

from rest_framework.decorators import api_view
from rest_framework.request import Request

from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
from wechatpy.events import UnsubscribeEvent, SubscribeEvent
from wechatpy.messages import TextMessage
from wechatpy.replies import TextReply, EmptyReply

from downloader.decorators import auth
from downloader.models import Version
from downloader.rsa import RSAUtil
from downloader.serializers import UserSerializers, PointRecordSerializers
from downloader.utils import ding


@api_view()
def get_version(request: Request):
    versions = Version.objects.order_by('-create_time').all()[:1]
    if len(versions) == 0:
        return JsonResponse(dict(code=404, msg='version not found'))

    version: Version = versions[0]
    create_time = int(version.create_time.timestamp())
    data = {
        'version': version.version,
        'create_time': create_time
    }
    return JsonResponse(dict(code=200, data=data))


@api_view(['POST'])
def update_version(request: Request):
    token = request.data.get('token')
    if token != settings.VERSION_TOKEN:
        return JsonResponse(dict(code=401, msg='未授权'))

    version = request.data.get('version')
    if not version:
        return JsonResponse(dict(code=400, msg='bad request'))
    try:
        Version.objects.create(version=version)
        ding(f'版本更新成功: {version}')
        return JsonResponse(dict(code=200, msg='version created'))
    except Exception as e:
        ding(f'版本发布失败: {e}')
        return JsonResponse(dict(code=500, msg='internal server error'))
