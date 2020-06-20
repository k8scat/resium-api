# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/6/20

"""
import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.models import SystemInfo
from downloader.serializers import SystemInfoSerializers


@api_view()
def get_system_info(request):
    system_info = SystemInfo.objects.get(id=1)
    return JsonResponse(dict(code=requests.codes.ok, system_info=SystemInfoSerializers(system_info).data))
