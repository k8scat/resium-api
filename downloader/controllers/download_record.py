import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import DownloadRecord
from downloader.serializers import DownloadRecordSerializers
from downloader.services.user import get_user_from_session
from downloader.utils.pagination import parse_pagination_args


@auth
@api_view()
def list_download_records(request):
    """
    获取用户所有的下载记录

    需要认证
    """
    user = get_user_from_session(request)
    if not user:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="用户不存在"))

    page, per_page = parse_pagination_args(request)
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
            download_records=DownloadRecordSerializers(
                download_records, many=True
            ).data,
        )
    )


@auth
@api_view()
def delete_download_record(request):
    download_record_id = request.GET.get("id", None)
    if not download_record_id:
        return JsonResponse(dict(code=400, msg="错误的请求"))

    try:
        download_record = DownloadRecord.objects.get(
            id=download_record_id, is_deleted=False
        )
        download_record.is_deleted = True
        download_record.save()
        return JsonResponse(dict(code=200, msg="下载记录删除成功"))

    except DownloadRecord.DoesNotExist:
        return JsonResponse(dict(code=404, msg="下载记录不存在"))
