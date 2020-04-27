# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/16

"""
import re
import string
from urllib import parse

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from rest_framework.decorators import api_view

from downloader.apis.resource import CsdnResource, WenkuResource, DocerResource, QiantuResource, ZhiwangResource
from downloader.models import User, DwzRecord, DownloadRecord
from downloader.utils import get_short_url, get_long_url, check_oss, aliyun_oss_sign_url


@api_view(['POST'])
def dwz(request):
    command = request.data.get('c', None)
    url = request.data.get('url', None)
    uid = request.data.get('uid', None)
    if not command or not url or not uid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)
        if DwzRecord.objects.filter(user=user, create_time__day=timezone.now().day).count() >= 100:
            return JsonResponse(dict(code=400, msg='今日请求数已达上限'))

    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='未认证'))

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

    DwzRecord(user=user, url=url, generated_url=generated_url).save()
    return JsonResponse(dict(code=200, url=generated_url))
