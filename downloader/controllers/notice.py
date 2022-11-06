import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.decorators import auth
from downloader.models import Notice
from downloader.serializers import NoticeSerializers


@api_view()
def get_notice(request: Request):
    notice = Notice.objects.first()
    if notice:
        return JsonResponse(
            dict(code=requests.codes.ok, notice=NoticeSerializers(notice).data)
        )
    else:
        return JsonResponse(dict(code=requests.codes.not_found, msg="公告不存在"))


@auth
@api_view(["POST"])
def update_notice(request):
    uid = request.session.get("uid")
    if uid not in settings.ADMIN_UID:
        return JsonResponse(dict(code=requests.codes.forbidden, msg="禁止请求"))

    title = request.data.get("title", "")
    content = request.data.get("content", "")
    notice = Notice.objects.first()
    if notice:
        notice.title = title
        notice.content = content
        notice.save()
    else:
        Notice.objects.create(title=title, content=content)
    return JsonResponse(dict(code=requests.codes.ok, msg="公告更新成功"))
