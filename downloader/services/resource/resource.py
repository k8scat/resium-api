import logging
import random
import re
import string
from typing import Dict

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from downloader.models import User, Resource, DownloadRecord, PointRecord
from downloader.serializers import UserSerializers, ResourceSerializers
from downloader.services.resource.types.base import BaseResource
from downloader.services.resource.types.csdn import CsdnResource
from downloader.services.resource.types.docer import DocerResource
from downloader.services.resource.types.wenku import WenkuResource
from downloader.utils import aliyun_oss
from downloader.utils.alert import alert


def new_resource(url: str, user: User) -> BaseResource | None:
    # CSDN资源
    if CsdnResource.is_valid_url(url):
        return CsdnResource(url, user)

    # 百度文库文档
    if WenkuResource.is_valid_url(url):
        return WenkuResource(url, user)

    # 稻壳模板
    if DocerResource.is_valid_url(url):
        return DocerResource(url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    # if re.match(settings.PATTERN_ZHIWANG, url):
    #     return ZhiwangResource(url, user)

    # if re.match(settings.PATTERN_QIANTU, url):
    #     return QiantuResource(url, user)

    # if re.match(settings.PATTERN_MBZJ, url):
    #     return MbzjResource(url, user)

    return None


def download_from_oss(resource: Resource, user: User, point: int) -> str:
    user.point -= point
    user.used_point += point
    user.save()

    DownloadRecord.objects.create(user=user, resource=resource, used_point=point)
    PointRecord.objects.create(
        user=user,
        used_point=point,
        comment="下载资源",
        url=resource.url,
        point=user.point,
    )

    # 生成临时下载地址，10分钟有效
    download_url = aliyun_oss.sign_url(resource.key)

    # 更新资源的下载次数
    resource.download_count += 1
    resource.save()

    try:
        subject = "[源自下载] 资源下载成功"
        html_message = render_to_string(
            "downloader/download_url.html", {"url": download_url}
        )
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        alert(
            "资源下载邮件发送失败",
            exception=e,
            user=UserSerializers(user).data,
            resource=ResourceSerializers(resource).data,
        )
    finally:
        return download_url


def get_oss_resource(url: str) -> Resource | None:
    try:
        resource = Resource.objects.get(url=url, is_audited=1)
        # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
        # 如果oss上没有存储资源，则提醒管理员检查资源
        if not aliyun_oss.check_file(resource.key):
            resource.delete()
            alert("资源存在记录，但找不到OSS存储", key=resource.key, url=resource.url)
            return None

        return resource

    except Resource.DoesNotExist:
        return None


def download(url: str, user: User) -> Dict:
    res = new_resource(url, user)
    if not res:
        return dict(code=requests.codes.bad_request, msg="下载地址有误")

    key = f"download_limit:{res.type()}:{user.uid}"
    if cache.get(key):
        return dict(code=requests.codes.forbidden, msg="请求频率过快，请稍后再试！")

    cache.set(key, True, timeout=settings.DOWNLOAD_INTERVAL)
    try:
        # 检查OSS是否存有该资源
        oss_resource = get_oss_resource(url)
        if oss_resource:
            point = res.resource["point"]
            if user.point < point:
                return dict(code=5000, msg="积分不足，请进行捐赠支持。")

            download_url = download_from_oss(oss_resource, user, point)
            return dict(code=requests.codes.ok, url=download_url)

        res.download()
        if res.err:
            if isinstance(res.err, dict):
                return dict(code=requests.codes.server_error, msg=res.err)

            return dict(code=requests.codes.server_error, msg=res.err)

        return dict(code=requests.codes.ok, url=res.download_url)

    finally:
        cache.delete(key)
