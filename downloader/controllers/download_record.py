import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import DownloadRecord, User
from downloader.serializers import DownloadRecordSerializers


@auth
@api_view()
def list_download_records(request):
    """
    获取用户所有的下载记录

    需要认证
    """
    uid = request.session.get("uid")
    user = User.objects.get(uid=uid)

    page = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 20)
    try:
        page = int(page)
        if page < 1:
            page = 1
        per_page = int(per_page)
        if per_page > 20:
            per_page = 20
    except ValueError:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    start = per_page * (page - 1)
    end = start + per_page

    download_records = (
        DownloadRecord.objects.filter(user=user, is_deleted=False)
        .order_by("-create_time")
        .all()[start:end]
    )
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            msg="获取下载记录成功",
            download_records=DownloadRecordSerializers(
                download_records, many=True
            ).data,
        )
    )


@auth
@api_view()
def delete_download_record(request):
    download_record_id = request.GET.get("id", None)
    if download_record_id:
        try:
            download_record = DownloadRecord.objects.get(
                id=download_record_id, is_deleted=False
            )
            download_record.is_deleted = True
            download_record.save()
            return JsonResponse(dict(code=200, msg="下载记录删除成功"))
        except DownloadRecord.DoesNotExist:
            return JsonResponse(dict(code=404, msg="下载记录不存在"))
    else:
        return JsonResponse(dict(code=400, msg="错误的请求"))
