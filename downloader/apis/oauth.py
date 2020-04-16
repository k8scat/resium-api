# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/5

"""
import datetime
import re
import time
import uuid

import jwt
import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view

from downloader.models import User


@api_view()
def qq(request):
    """
    http://localhost:8000/oauth/qq?code=F89BF43543BE4C339789F7EF3980C4E4&state=success

    返回示例: https://api.resium.cn/oauth/qq?code=96454463D7D89DB61ACBCE2FCD7E4041&state=success

    :param request:
    :return:
    """

    response = redirect('https://resium.cn')

    code = request.GET.get('code', None)
    state = request.GET.get('state', None)
    if code or state == 'success':
        params = {
            'grant_type': 'authorization_code',
            'client_id': settings.QQ_CLIENT_ID,
            'client_secret': settings.QQ_CLIENT_SECRET,
            'code': code,
            'redirect_uri': 'https://api.resium.cn/oauth/qq'
        }
        with requests.get('https://graph.qq.com/oauth2.0/token', params=params) as get_access_token_resp:
            if get_access_token_resp.status_code == requests.codes.OK:
                if re.match(r'^access_token=.+&expires_in=\d+&refresh_token=.+$', get_access_token_resp.text):
                    data = {param.split('=')[0]: param.split('=')[1] for param in get_access_token_resp.text.split('&')}
                    access_token = data['access_token']
                    params = {
                        'access_token': access_token
                    }
                    with requests.get('https://graph.qq.com/oauth2.0/me', params=params) as get_openid_resp:
                        # callback( {"client_id":"101864025","openid":"C0207FA138ECDA39D1504427C82C3001"} );
                        if get_openid_resp.status_code == requests.codes.OK:
                            if re.match(r'^callback\( {"client_id":".+","openid":".+"} \);$', get_openid_resp.text):
                                qq_openid = get_openid_resp.text.split('callback( {"client_id":"')[1].split('","openid":"')[0]
                                login_time = datetime.datetime.now()
                                try:
                                    user = User.objects.get(qq_openid=qq_openid)
                                    user.login_time = login_time
                                    user.save()

                                except User.DoesNotExist:
                                    params = {
                                        'access_token': access_token,
                                        'oauth_consumer_key': settings.QQ_CLIENT_ID,
                                        'openid': qq_openid
                                    }
                                    with requests.get('https://graph.qq.com/user/get_user_info', params=params) as get_user_info_resp:
                                        if get_user_info_resp.status_code == requests.codes.OK:
                                            data = get_user_info_resp.json()
                                            if data['ret'] == 0:
                                                nickname = data['nickname']
                                                avatar_url = data['figureurl_2']
                                        else:
                                            return response

                                    uid = f"{str(uuid.uuid1()).replace('-', '')}.{str(time.time())}"
                                    User.objects.create(uid=uid, qq_openid=qq_openid, nickname=nickname,
                                                        avatar_url=avatar_url, login_time=login_time)

                                # 设置token过期时间
                                exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
                                payload = {
                                    'exp': exp,
                                    'sub': user.uid
                                }
                                token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS512').decode()
                                # 设置cookie
                                response.set_cookie('token', token, domain='resium.cn')

    return response


@api_view()
def github(request):
    return HttpResponse('oauth github')


@api_view()
def gitee(request):
    return HttpResponse('oauth gitee')

