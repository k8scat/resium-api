# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

"""
import json
import re

import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.models import User, CsdnAccount
from downloader.serializers import UserSerializers, CsdnAccountSerializers


@api_view(['POST'])
def set_user_can_download(request):
    token = request.data.get('token', None)
    uid = request.data.get('uid', None)
    if token != settings.BOT_TOKEN or not uid:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)

        if user.can_download:
            return JsonResponse(dict(code=requests.codes.bad_request, msg='该账号已开启外站资源下载功能'))

        user.can_download = True
        user.save()
        return JsonResponse(dict(code=requests.codes.ok, msg='成功设置用户可下载外站资源'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='用户不存在'))


@api_view(['POST'])
def get_user(request):
    token = request.data.get('token', None)
    uid = request.data.get('uid', None)
    if token != settings.BOT_TOKEN or not uid:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)

        return JsonResponse(dict(code=requests.codes.ok, user=UserSerializers(user).data))
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='用户不存在'))


@api_view(['POST'])
def set_csdn_sms_validate_code(request):
    """
    保存CSDN下载短信验证码到数据库

    :param request:
    :return:
    """

    token = request.data.get('token', None)
    email = request.data.get('email', None)
    code = request.data.get('code', None)
    if token != settings.BOT_TOKEN or not code or not email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        account = CsdnAccount.objects.get(email=email, need_sms_validate=True)
        account.sms_code = code
        account.save()

        return JsonResponse(dict(code=requests.codes.ok, msg='验证码保存成功'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='账号不存在'))


@api_view(['POST'])
def list_csdn_accounts(request):
    """
    获取csdn账号信息

    :param request:
    :return:
    """

    token = request.data.get('token', None)
    if token != settings.BOT_TOKEN:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))
    accounts = CsdnAccount.objects.all()
    msg = ''
    for index, account in enumerate(accounts):
        msg += json.dumps(CsdnAccountSerializers(account).data)
        if index < len(accounts)-1:
            msg += '\n\n'

    return JsonResponse(dict(code=requests.codes.ok, msg=msg))


@api_view()
def activate_taobao_user(request):
    uid = request.data.get('uid', None)
    token = request.data.get('token', None)
    if token != settings.BOT_TOKEN or not re.match(r'^\d{6}$', uid):
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)
        if user.can_download:
            return JsonResponse(dict(code=requests.codes.bad_request, msg='淘宝用户只能购买一次'))
        user.point += 10
        user.can_download = True
        user.from_taobao = True
        user.save()
        return JsonResponse(dict(code=requests.codes.ok, msg='成功授权并发放积分'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='用户不存在'))
