# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/9

"""
from django.conf import settings
from django.http import JsonResponse

from downloader.decorators import auth
from downloader.serializers import ServiceSerializers, Service


def list_services(request):
    """
    获取所有的服务
    """

    if request.method == 'GET':
        services = Service.objects.all()
        return JsonResponse(dict(code=200, services=ServiceSerializers(services, many=True).data))


def list_points(request):
    """
    获取所有下载所需的积分
    """

    if request.method == 'GET':
        points = {
            'wenku_vip_free': settings.WENKU_VIP_FREE_DOC_POINT,
            'wenku_share_doc': settings.WENKU_SHARE_DOC_POINT,
            'wenku_special_doc': settings.WENKU_SPECIAL_DOC_POINT,
            'csdn': settings.CSDN_POINT,
            'csdn_pro': settings.CSDN_PRO_POINT,
            'zhiwang': settings.ZHIWANG_POINT,
            'docer': settings.DOCER_POINT,
            'oss_resource': settings.OSS_RESOURCE_POINT,
            'article': settings.ARTICLE_POINT
        }
        return JsonResponse(dict(code=200, points=points))
