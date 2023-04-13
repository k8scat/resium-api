import logging
import random

import requests
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.decorators import auth
from downloader.models import *
from downloader.serializers import (
    ResourceSerializers,
    ResourceCommentSerializers,
)
from downloader.services.resource.resource import (
    new_resource,
    download_from_oss,
    download as _download,
)
from downloader.services.resource.types.csdn import CsdnResource
from downloader.services.resource.types.docer import DocerResource
from downloader.services.user import get_user_from_session
from downloader.utils import aliyun_oss
from downloader.utils.pagination import parse_pagination_args


@auth
@api_view()
def check_file(request):
    """
    根据md5值判断资源是否存在

    :param request:
    :return:
    """

    file_md5 = request.GET.get("hash", None)
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源已存在"))
    return JsonResponse(dict(code=requests.codes.ok, msg="资源不存在"))


@api_view()
def get_resource(request):
    resource_id = request.GET.get("id", None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
        try:
            resource = Resource.objects.get(id=resource_id, is_audited=1)
            preview_images = []
            if resource.url and DocerResource.is_valid_url(resource.url):
                preview_images = [
                    {"url": preview_image.url, "alt": preview_image.alt}
                    for preview_image in DocerPreviewImage.objects.filter(
                        resource_url=resource.url
                    ).all()
                ]
            resource_ = ResourceSerializers(resource).data
            # todo: 可以尝试通过django-rest-framework实现，而不是手动去获取预览图的数据
            resource_.setdefault("preview_images", preview_images)
            resource_.setdefault(
                "point", settings.OSS_RESOURCE_POINT + resource.download_count - 1
            )
            return JsonResponse(dict(code=requests.codes.ok, resource=resource_))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=404, msg="资源不存在"))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))


@api_view()
def list_resource_comments(request):
    resource_id = request.GET.get("id", None)
    if not resource_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        resource = Resource.objects.get(id=resource_id)
        comments = (
            ResourceComment.objects.filter(resource=resource)
            .order_by("-create_time")
            .all()
        )
        return JsonResponse(
            dict(
                code=requests.codes.ok,
                comments=ResourceCommentSerializers(comments, many=True).data,
            )
        )
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))


@auth
@api_view(["POST"])
def create_resource_comment(request):
    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    content = request.data.get("content", None)
    resource_id = request.data.get("id", None)
    if not content or not resource_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        resource = Resource.objects.get(id=resource_id, is_audited=1)
        resource_comment = ResourceComment.objects.create(
            user=user, resource=resource, content=content
        )
        return JsonResponse(
            dict(
                code=requests.codes.ok,
                msg="评论成功",
                comment=ResourceCommentSerializers(resource_comment).data,
            )
        )
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))


@api_view()
def list_resources(request):
    """
    分页获取资源
    """
    page, per_page = parse_pagination_args(request)
    start = per_page * (page - 1)
    end = start + per_page

    key = request.GET.get("key", "")

    query = (Q(is_audited=1),)
    if key:
        query += (
            Q(title__icontains=key) | Q(desc__icontains=key) | Q(tags__icontains=key),
        )
    else:
        query += (~Q(url__startswith="https://www.docer.com"),)

    # Django模型-不区分大小写的查询/过滤 https://cloud.tencent.com/developer/ask/81558
    resources = (
        Resource.objects.filter(*query).order_by("-create_time").all()[start:end]
    )
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            resources=ResourceSerializers(resources, many=True).data,
        )
    )


@api_view()
def get_resource_count(request: Request):
    """
    获取资源的数量
    """
    key = request.GET.get("key", "")
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            count=Resource.objects.filter(
                Q(is_audited=1),
                Q(title__icontains=key)
                | Q(desc__icontains=key)
                | Q(tags__icontains=key),
            ).count(),
        )
    )


@api_view()
def list_resource_tags(request: Request):
    """
    获取所有的资源标签
    """
    tags = Resource.objects.values_list("tags")
    ret_tags = []
    for tag in tags:
        for t in tag[0].split(settings.TAG_SEP):
            if t not in ret_tags and t != "":
                ret_tags.append(t)

    return JsonResponse(
        dict(
            code=requests.codes.ok,
            tags=settings.TAG_SEP.join(
                random.sample(ret_tags, settings.SAMPLE_TAG_COUNT)
            ),
        )
    )


@auth
@api_view(["POST"])
def download(request: Request):
    resource_url = request.data.get("url", None)
    if not resource_url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源地址不能为空"))

    user = get_user_from_session(request)

    resp = _download(resource_url, user)
    return JsonResponse(resp)


@auth
@api_view()
def oss_download(request: Request):
    resource_id = request.GET.get("id", None)
    if not resource_id or not resource_id.isnumeric():
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    resource_id = int(resource_id)
    user = get_user_from_session(request)
    try:
        oss_resource = Resource.objects.get(id=resource_id)
        if not aliyun_oss.check_file(oss_resource.key):
            logging.error(f"oss resource not exists: {oss_resource.key}")
            if CsdnResource.is_valid_url(oss_resource.url):
                logging.info(f"retry download resource: {oss_resource.url}")
                resp = _download(oss_resource.url, user)
                return JsonResponse(resp)

            return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))

    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))

    point = settings.OSS_RESOURCE_POINT + oss_resource.download_count - 1
    if user.point < point:
        return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

    download_url = download_from_oss(oss_resource, user, point)
    return JsonResponse(dict(code=requests.codes.ok, url=download_url))


@auth
@api_view(["POST"])
def parse_resource(request):
    """
    爬取资源信息

    返回资源信息以及相关资源信息

    :param request:
    :return:
    """

    resource_url = request.data.get("url", None)
    if not resource_url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    uid = request.session.get("uid")
    user = User.objects.get(uid=uid)

    res = new_resource(resource_url, user)
    if not res:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="下载地址有误"))
    res.parse()
    return JsonResponse(dict(code=requests.codes.ok, resource=res.resource))


@auth
@api_view(["POST"])
def check_resource_existed(request):
    url = request.data.get("url", None)
    if not url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    is_resource_existed = Resource.objects.filter(url=url).count() > 0
    return JsonResponse(dict(code=requests.codes.ok, is_existed=is_resource_existed))
