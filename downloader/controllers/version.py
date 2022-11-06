import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.models import Version
from downloader.serializers import VersionSerializers
from downloader.utils.alert import alert


@api_view()
def get_latest_version(request: Request):
    version = Version.objects.order_by("-create_time").first()
    if not version:
        return JsonResponse(
            dict(code=requests.codes.not_found, msg="version not found")
        )

    return JsonResponse(
        dict(code=requests.codes.ok, data=VersionSerializers(version).data)
    )


@api_view(["POST"])
def create_version(request: Request):
    token = request.data.get("token")
    if token != settings.VERSION_TOKEN:
        return JsonResponse(dict(code=requests.codes.forbidden))

    version = request.data.get("version")
    if not version:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="bad request"))

    Version.objects.create(version=version)
    alert("版本更新成功", version=version)
    return JsonResponse(dict(code=requests.codes.ok, msg="version created"))
