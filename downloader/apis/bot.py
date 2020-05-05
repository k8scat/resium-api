# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

"""
import json

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view
from downloader.models import User
from downloader.serializers import UserSerializers


@api_view(['POST'])
def set_user_can_download(request):
    token = request.data.get('token', None)
    uid = request.data.get('uid', None)
    if token != settings.BOT_TOKEN or not uid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)

        if user.can_download:
            return JsonResponse(dict(code=400, msg='该账号已开启外站资源下载功能'))

        user.can_download = True
        user.save()
        return JsonResponse(dict(code=200, msg='成功设置用户可下载外站资源'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='用户不存在'))


@api_view()
def get_user(request):
    token = request.data.get('token', None)
    uid = request.data.get('uid', None)
    if token != settings.BOT_TOKEN or not uid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)

        return JsonResponse(dict(code=200, user=UserSerializers(user).data))
    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='用户不存在'))
