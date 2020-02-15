# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
import logging
import uuid

from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view

from downloader import params
from downloader.decorators import auth
from downloader.models import Resource, User
from downloader.serializers import ResourceSerializers
from downloader.utils import aliyun_oss_upload, get_file_md5, ding


@auth
def upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file', None)
        file_md5 = get_file_md5(file.open('rb'))
        if Resource.objects.filter(file_md5=file_md5).count():
            return JsonResponse(dict(code=400, msg='资源已存在'))

        data = request.POST
        title = data.get('title', None)
        tags = data.get('tags', None)
        desc = data.get('desc', None)
        category = data.get('category', None)
        if title and tags and desc and category and file:
            try:
                email = request.session.get('email')
                try:
                    user = User.objects.get(email=email, is_active=True)
                except User.DoesNotExist:
                    return JsonResponse(dict(code=400, msg='错误的请求'))

                key = f'{str(uuid.uuid1())}-{file.name}'
                logging.info(f'Upload resource: {key}')
                if aliyun_oss_upload(file, key):
                    Resource(title=title, desc=desc, tags=tags,
                             category=category, filename=file.name, size=file.size,
                             is_audited=False, key=key, user=user, file_md5=file_md5,
                             download_count=0).save()
                    ding(f'有新的资源上传 {file.name}')
                    return JsonResponse(dict(code=200, msg='资源上传成功'))
                else:
                    return JsonResponse(dict(code=500, msg='资源上传失败'))
            except Exception as e:
                logging.error(e)
                return JsonResponse(dict(code=500, msg='资源上传失败'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@swagger_auto_schema(method='get', manual_parameters=[params.file_md5])
@api_view(['GET'])
def check_file(request):
    if request.method == 'GET':
        file_md5 = request.GET.get('hash', None)
        if Resource.objects.filter(file_md5=file_md5).count():
            return JsonResponse(dict(code=400, msg='资源已存在'))
        return JsonResponse(dict(code=200, msg='资源不存在'))


@auth
def list_uploaded_resources(request):
    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email)
            resources = Resource.objects.order_by('-create_time').filter(user=user).all()
            return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))
        except User.DoesNotExist:
            return JsonResponse(dict(code=400, msg='错误的请求'))
