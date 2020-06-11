# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
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
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg='未登录'))

    download_records = DownloadRecord.objects.order_by('-create_time').filter(user=user, is_deleted=False).all()
    return JsonResponse(dict(code=requests.codes.ok, msg='获取下载记录成功',
                             download_records=DownloadRecordSerializers(download_records, many=True).data))


@auth
@api_view()
def delete_download_record(request):
    download_record_id = request.GET.get('id', None)
    if download_record_id:
        try:
            download_record = DownloadRecord.objects.get(id=download_record_id, is_deleted=False)
            download_record.is_deleted = True
            download_record.save()
            return JsonResponse(dict(code=200, msg='下载记录删除成功'))
        except DownloadRecord.DoesNotExist:
            return JsonResponse(dict(code=404, msg='下载记录不存在'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))
