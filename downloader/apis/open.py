# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/16

"""
import os
import re
import string
import uuid
from urllib import parse

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, FileResponse
from rest_framework.decorators import api_view

from downloader.apis.resource import CsdnResource, WenkuResource, DocerResource, QiantuResource, ZhiwangResource
from downloader.models import User, DwzRecord, DownloadRecord
from downloader.utils import get_short_url, get_long_url, check_oss, aliyun_oss_sign_url


@api_view(['POST'])
def dwz(request):
    command = request.data.get('c', None)
    url = request.data.get('url', None)
    uid = request.data.get('uid', None)
    if not command or not url or not uid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='未认证'))

    if command == 'create':
        # 生成一年有效的短网址
        generated_url = get_short_url(url)

        if not generated_url:
            return JsonResponse(dict(code=500, msg='短网址创建失败'))

    elif command == 'reduce':
        if not re.match(r'^(https://dwz\.cn/).+$', url):
            return JsonResponse(dict(code=400, msg='无效的短网址'))

        generated_url = get_long_url(url)
        if not generated_url:
            return JsonResponse(dict(code=500, msg='短网址还原失败'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    DwzRecord(user=user, url=url, generated_url=generated_url).save()
    return JsonResponse(dict(code=200, url=generated_url))


@api_view(['POST'])
def download(request):
    uid = request.data.get('uid', None)
    resource_url = request.data.get('url', None)
    if not uid or not resource_url:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)
        cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未认证'))

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    # 检查OSS是否存有该资源
    oss_resource = check_oss(resource_url)
    if oss_resource:
        point = request.data.get('point', None)
        if point is None or \
                (re.match(settings.PATTERN_CSDN, resource_url) and point != settings.CSDN_POINT) or \
                (re.match(settings.PATTERN_WENKU, resource_url) and point not in [settings.WENKU_SHARE_DOC_POINT,
                                                                                  settings.WENKU_SPECIAL_DOC_POINT,
                                                                                  settings.WENKU_VIP_FREE_DOC_POINT]) or \
                (re.match(settings.PATTERN_DOCER, resource_url) and point != settings.DOCER_POINT) or \
                (re.match(settings.PATTERN_ZHIWANG, resource_url) and point != settings.ZHIWANG_POINT) or \
                (re.match(settings.PATTERN_QIANTU, resource_url) and point != settings.QIANTU_POINT):
            return JsonResponse(dict(code=400, msg='错误的请求'))

        if user.point < point:
            return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

        # 判断用户是否下载过该资源
        # 若没有，则给上传资源的用户赠送积分
        if user != oss_resource.user:
            if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
                oss_resource.user.point += 1
                oss_resource.user.save()

        # 新增下载记录
        DownloadRecord(user=user,
                       resource=oss_resource,
                       used_point=point).save()
        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()

        # 生成临时下载地址，10分钟有效
        url = get_short_url(aliyun_oss_sign_url(oss_resource.key))

        # 更新资源的下载次数
        oss_resource.download_count += 1
        oss_resource.save()

        return JsonResponse(dict(code=200, url=url))

    # CSDN资源下载
    if re.match(settings.PATTERN_CSDN, resource_url):
        resource = CsdnResource(resource_url, user)

    # 百度文库文档下载
    elif re.match(settings.PATTERN_WENKU, resource_url):
        resource = WenkuResource(resource_url, user)

    # 稻壳模板下载
    elif re.match(settings.PATTERN_DOCER, resource_url):
        resource = DocerResource(resource_url, user)

    elif re.match(settings.PATTERN_QIANTU, resource_url):
        resource = QiantuResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        resource = ZhiwangResource(resource_url, user)

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    status, result = resource.download()
    if status != 200:
        return JsonResponse(dict(code=status, msg=result))

    response = FileResponse(open(result['filepath'], 'rb'))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(result['filename'],
                                                                            safe=string.printable) + '"'
    return response
