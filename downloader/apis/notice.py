# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/7/25

"""
import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import Notice
from downloader.serializers import NoticeSerializers


@api_view()
def get_notice(request):
    try:
        notice = Notice.objects.get(id=1)
        return JsonResponse(dict(code=200, notice=NoticeSerializers(notice).data))
    except Notice.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='公告不存在'))


@auth
@api_view(['POST'])
def update_notice(request):
    uid = request.session.get('uid')
    if uid not in settings.ADMIN_UID:
        return JsonResponse(dict(code=requests.codes.forbidden, msg='禁止请求'))

    title = request.data.get('title', None)
    content = request.data.get('content', None)
    try:
        notice = Notice.objects.get(id=1)
        if title:
            notice.title = title
        if content:
            notice.content = content
        notice.save()
        return JsonResponse(dict(code=requests.codes.ok, msg='公告更新成功'))

    except Notice.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='公告不存在'))

