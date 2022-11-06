import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.serializers import ServiceSerializers, Service


@api_view()
def list_services(request: Request):
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            services=ServiceSerializers(Service.objects.all(), many=True).data,
        )
    )
