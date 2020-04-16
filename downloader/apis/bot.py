# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

"""
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view
from downloader.models import User


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
