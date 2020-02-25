# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/9

"""
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from downloader.serializers import ServiceSerializers, Service


@swagger_auto_schema(method='get')
@api_view(['GET'])
def list_services(request):
    """
    获取所有的服务
    """

    if request.method == 'GET':
        services = Service.objects.all()
        return JsonResponse(dict(code=200, services=ServiceSerializers(services, many=True).data))


