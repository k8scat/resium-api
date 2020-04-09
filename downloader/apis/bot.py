# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

"""
import re

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.apis.resource import CsdnResource, WenkuResource, DocerResource, ZhiwangResource
from downloader.models import User, DownloadRecord
from downloader.utils import check_oss, ding, aliyun_oss_sign_url


@api_view(['POST'])
def download(request):
    token = request.data.get('token', None)
    if not token or token != settings.BOT_TOKEN:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    qq = request.data.get('qq', None)
    url = request.data.get('url', None)
    if not qq or not url:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    if cache.get(str(qq)):
        return JsonResponse(dict(code=403, msg='下载请求过快，请稍后再尝试！'))

    try:
        user = User.objects.get(qq=qq, is_active=True)
        cache.set(str(qq), True, timeout=settings.COOLQ_DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='请先前往源自下载网站的个人中心进行绑定QQ！'))

    # 检查OSS是否存有该资源
    oss_resource = check_oss(url)
    if oss_resource:
        # CSDN资源
        if re.match(settings.PATTERN_CSDN, url):
            point = settings.CSDN_POINT

        # 百度文库文档
        elif re.match(settings.PATTERN_WENKU, url):
            if oss_resource.wenku_type == 'VIP免费文档':
                point = settings.WENKU_VIP_FREE_DOC_POINT
            elif oss_resource.wenku_type == 'VIP专享文档':
                point = settings.WENKU_SPECIAL_DOC_POINT
            elif oss_resource.wenku_type == '共享文档':
                point = settings.WENKU_SHARE_DOC_POINT
            else:
                ding('[百度文库] 已有百度文库文档的类型获取失败',
                     resource_url=url,
                     qq=qq)
                return JsonResponse(dict(code=500, msg='资源获取失败'))

        # 稻壳模板
        elif re.match(settings.PATTERN_DOCER, url):
            point = settings.DOCER_POINT

        elif re.match(settings.PATTERN_ZHIWANG, url):
            point = settings.ZHIWANG_POINT

        else:
            return JsonResponse(dict(code=400, msg='无效的资源地址'))

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
                       download_device=user.login_device,
                       download_ip=user.login_ip,
                       used_point=point).save()
        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()

        # 生成临时下载地址
        download_url = aliyun_oss_sign_url(oss_resource.key)

        # 更新资源的下载次数
        oss_resource.download_count += 1
        oss_resource.save()

        return JsonResponse(dict(code=200, download_url=download_url, point=point))

    # CSDN资源下载
    if re.match(settings.PATTERN_CSDN, url):
        resource = CsdnResource(url, user)

    # 百度文库文档下载
    elif re.match(settings.PATTERN_WENKU, url):
        resource = WenkuResource(url, user)

    # 稻壳模板下载
    elif re.match(settings.PATTERN_DOCER, url):
        resource = DocerResource(url, user)

    elif re.match(settings.PATTERN_ZHIWANG, url):
        resource = ZhiwangResource(url, user)

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    status, result = resource.download(ret_url=True)
    if status != 200:
        return JsonResponse(dict(code=status, msg=result))
    return JsonResponse(dict(code=200, download_url=result['download_url'], point=result['point']))


@api_view(['POST'])
def check_can_download(request):
    token = request.data.get('token', None)
    if not token or token != settings.BOT_TOKEN:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    qq = request.data.get('qq', None)
    if not qq:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    if cache.get(str(qq)):
        return JsonResponse(dict(code=403, msg='下载请求过快，请稍后再尝试！'))

    if not User.objects.filter(qq=qq, is_active=True).count():
        return JsonResponse(dict(code=401, msg='请先前往源自下载网站的个人中心进行绑定QQ！'))

    return JsonResponse(dict(code=200, msg='ok'))


@api_view(['POST'])
def set_user_can_download(request):
    token = request.data.get('token', None)
    email = request.data.get('email', None)
    if not token or not email or token != settings.BOT_TOKEN:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(email=email, is_active=True)
        if not user.phone:
            return JsonResponse(dict(code=400, msg='用户为绑定手机号'))

        if user.can_download:
            return JsonResponse(dict(code=400, msg='该账号已开启外站资源下载功能'))

        user.can_download = True
        user.save()
        return JsonResponse(dict(code=200, msg='成功设置用户可下载外站资源'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='用户不存在'))
