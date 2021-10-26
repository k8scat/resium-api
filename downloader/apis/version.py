# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2021/10/22

"""
from django.conf import settings
from django.http import JsonResponse

from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.models import Version
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
