# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
import logging
import os
import uuid
from itertools import chain
from threading import Thread

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader import params
from downloader.decorators import auth
from downloader.models import Resource, User, ResourceComment
from downloader.serializers import ResourceSerializers, ResourceCommentSerializers
from downloader.utils import aliyun_oss_upload, get_file_md5, ding


@auth
@api_view(['POST'])
def upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file', None)

        # 向上扩大一点
        if file.size > (2 * 100 + 10) * 1024 * 1024:
            return JsonResponse(dict(code=400, msg='上传资源大小不能超过200MB'))

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
                filepath = os.path.join(settings.UPLOAD_DIR, key)
                # 写入文件，之后使用线程进行上传
                with open(filepath, 'wb') as f:
                    for chunk in file.chunks():
                        f.write(chunk)
                Resource(title=title, desc=desc, tags=tags,
                         category=category, filename=file.name, size=file.size,
                         is_audited=False, key=key, user=user, file_md5=file_md5,
                         download_count=0).save()

                # 开线程上传资源到OSS
                t = Thread(target=aliyun_oss_upload, args=(filepath, key))
                t.start()

                ding(f'有新的资源上传 {file.name}')
                return JsonResponse(dict(code=200, msg='资源上传成功'))
            except Exception as e:
                logging.error(e)
                return JsonResponse(dict(code=500, msg='资源上传失败'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@swagger_auto_schema(method='get', manual_parameters=[params.file_md5])
@api_view(['GET'])
def check_file(request):
    """
    根据md5值判断资源是否存在

    :param request:
    :return:
    """

    if request.method == 'GET':
        file_md5 = request.GET.get('hash', None)
        if Resource.objects.filter(file_md5=file_md5).count():
            return JsonResponse(dict(code=400, msg='资源已存在'))
        return JsonResponse(dict(code=200, msg='资源不存在'))


@auth
@api_view(['GET'])
def list_uploaded_resources(request):
    """
    获取用户上传资源

    :param request:
    :return:
    """

    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email)
            resources = Resource.objects.order_by('-create_time').filter(user=user).all()
            return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))
        except User.DoesNotExist:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def get_resource_by_id(request):
    if request.method == 'GET':
        resource_id = request.GET.get('id', None)
        if resource_id:
            try:
                resource = Resource.objects.get(id=resource_id, is_audited=1)
                return JsonResponse(dict(code=200, resource=ResourceSerializers(resource).data))
            except Resource.DoesNotExist:
                return JsonResponse(dict(code=404, msg='资源不存在'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def list_comments(request):
    if request.method == 'GET':
        resource_id = request.GET.get('resource_id', None)
        if resource_id:
            try:
                comments = ResourceComment.objects.filter(resource_id=resource_id).all()
                return JsonResponse(dict(code=200, comments=ResourceCommentSerializers(comments, many=True).data))
            except Resource.DoesNotExist:
                return JsonResponse(dict(code=404, msg='资源不存在'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@ratelimit(key='ip', rate='1/5m', block=True)
@auth
@api_view(['POST'])
def create_comment(request):
    if request.method == 'POST':
        content = request.data.get('content', None)
        resource_id = request.data.get('resource_id', None)
        user_id = request.data.get('user_id', None)
        if content and resource_id and user_id:
            try:
                resource = Resource.objects.get(id=resource_id, is_audited=1)
                user = User.objects.get(id=user_id)
                ResourceComment(user=user, resource=resource, content=content).save()
                return JsonResponse(dict(code=200, msg='评论成功'))
            except (User.DoesNotExist, Resource.DoesNotExist):
                return JsonResponse(dict(code=400, msg='错误的请求'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def list_related_resources(request: Request):
    if request.method == 'GET':
        # 这个id好像不需要转换成int类型的，查询没有报错
        resource_id = request.GET.get('resource_id', None)
        if resource_id:
            try:
                resource = Resource.objects.get(id=resource_id)
                tags = resource.tags.split(settings.TAG_SEP)
                if resource.tags and len(tags):
                    resources = []
                    for tag in tags:
                        resources = list(chain(resources, Resource.objects.filter(~Q(id=resource_id), Q(is_audited=1),
                                                                             Q(tags__icontains=tag) |
                                                                             Q(title__icontains=tag) |
                                                                             Q(desc__icontains=tag)).all()[:10]))

                    # 调用list后，resources变为空了
                    resources_count = len(resources)
                    if resources_count != 10:
                        # 使用chain合并多个queryset
                        resources = chain(resources,
                                          Resource.objects.order_by('-download_count').filter(~Q(id=resource_id),
                                                                                              Q(is_audited=1)).all()[:10-resources_count])

                else:
                    resources = Resource.objects.order_by('-download_count').filter(~Q(id=resource_id),
                                                                                    Q(is_audited=1)).all()[:10]
                return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))
            except Resource.DoesNotExist:
                return JsonResponse(dict(code=404, msg='资源不存在'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))
