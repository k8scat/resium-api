# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/16

"""
import re

from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import User, DwzRecord
from downloader.utils import get_short_url, get_long_url


@auth
@api_view(['POST'])
def dwz(request):
    command = request.data.get('c', None)
    url = request.data.get('url', None)
    if not command or not url:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='未认证'))

    point = 0
    if command == 'create':
        # 生成一年有效的短网址
        generated_url = get_short_url(url)

        if not generated_url:
            return JsonResponse(dict(code=500, msg='短网址创建失败'))

    elif command == 'reduce':
        if not re.match(r'^(https://dwz\.cn/).+$', url):
            return JsonResponse(dict(code=400, msg='无效的短网址'))

        generated_url = get_long_url(url)
        if not generated_url:
            return JsonResponse(dict(code=500, msg='短网址还原失败'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    DwzRecord(user=user, url=url, generated_url=generated_url, point=point).save()
    return JsonResponse(dict(code=200, url=generated_url))
