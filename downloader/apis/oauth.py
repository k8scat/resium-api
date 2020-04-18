# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/5

"""
import datetime
import logging
import re
import time
from urllib import parse

import jwt
import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.decorators import api_view

from downloader.models import User
from downloader.utils import generate_uid, generate_jwt, get_ding_talk_signature


@api_view()
def dev(request):
    if settings.DEBUG:
        response = redirect(settings.RESIUM_UI)

        # 设置token过期时间
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        payload = {
            'exp': exp,
            'sub': settings.DEV_UID  # 这里设置的本地数据库用户的uid
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS512').decode()

        # 设置cookie
        response.set_cookie(settings.JWT_COOKIE_KEY, token, domain=settings.COOKIE_DOMAIN)

        return response


@api_view()
def qq(request):
    """
    http://localhost:8000/oauth/qq?code=F89BF43543BE4C339789F7EF3980C4E4&state=success

    返回示例: https://api.resium.cn/oauth/qq?code=96454463D7D89DB61ACBCE2FCD7E4041&state=success

    :param request:
    :return:
    """
    response = redirect(settings.RESIUM_UI)

    code = request.GET.get('code', None)
    if code:
        params = {
            'grant_type': 'authorization_code',
            'client_id': settings.QQ_CLIENT_ID,
            'client_secret': settings.QQ_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.QQ_REDIRECT_URI
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
                                qq_openid = get_openid_resp.text.split('","openid":"')[1].split('"')[0]
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
                                            avatar_url = data.get('figureurl_qq_2', None)
                                            if not avatar_url:
                                                avatar_url = data.get('figureurl_2')
                                            uid = generate_uid()
                                            login_time = datetime.datetime.now()
                                            try:
                                                user = User.objects.get(qq_openid=qq_openid)
                                                user.nickname = nickname
                                                user.avatar_url = avatar_url
                                                user.login_time = login_time
                                                user.save()
                                            except User.DoesNotExist:
                                                user = User.objects.create(uid=uid, qq_openid=qq_openid,
                                                                           nickname=nickname, avatar_url=avatar_url,
                                                                           login_time=login_time)

                                            if user:
                                                token = generate_jwt(user.uid)
                                                # 设置cookie
                                                response.set_cookie(settings.JWT_COOKIE_KEY, token, domain=settings.COOKIE_DOMAIN)

    return response


@api_view()
def github(request):
    response = redirect(settings.RESIUM_UI)

    code = request.GET.get('code', None)
    if code:
        data = {
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_CLIENT_SECRET,
            'code': code
        }
        with requests.post('https://github.com/login/oauth/access_token', data) as get_access_token_resp:
            if get_access_token_resp.status_code == requests.codes.OK:
                # content: access_token=e72e16c7e42f292c6912e7710c838347ae178b4a&token_type=bearer
                access_token = get_access_token_resp.text.split('&')[0].split('=')[1]
                headers = {
                    'Authorization': f'token {access_token}'
                }

                with requests.get('https://api.github.com/user', headers=headers) as get_user_resp:
                    if get_user_resp.status_code == requests.codes.OK:
                        # Refer: https://developer.github.com/v3/users/#get-a-single-user
                        github_user = get_user_resp.json()
                        github_id = github_user['id']
                        nickname = github_user['login']
                        avatar_url = github_user['avatar_url']
                        login_time = datetime.datetime.now()
                        try:
                            user = User.objects.get(github_id=github_id)
                            user.nickname = nickname
                            user.avatar_url = avatar_url
                            user.login_time = login_time
                            user.save()
                        except User.DoesNotExist:
                            uid = generate_uid()
                            user = User.objects.create(uid=uid, github_id=github_id,
                                                       nickname=nickname, avatar_url=avatar_url,
                                                       login_time=login_time)

                        if user:
                            token = generate_jwt(user.uid)
                            response.set_cookie(settings.JWT_COOKIE_KEY, token, domain=settings.COOKIE_DOMAIN)

    return response


@api_view()
def gitee(request):
    response = redirect(settings.RESIUM_UI)

    code = request.GET.get('code', None)
    if code:
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': settings.GITEE_CLIENT_ID,
            'client_secret': settings.GITEE_CLIENT_SECRET,
            'redirect_uri': settings.GITEE_REDIRECT_URI
        }
        with requests.post('https://gitee.com/oauth/token', params=params) as get_access_token_resp:
            if get_access_token_resp.status_code == requests.codes.OK:
                access_token = get_access_token_resp.json()['access_token']
                params = {
                    'access_token': access_token
                }

                with requests.get('https://gitee.com/api/v5/user', params=params) as get_user_resp:
                    if get_user_resp.status_code == requests.codes.OK:
                        gitee_user = get_user_resp.json()
                        gitee_id = gitee_user['id']
                        nickname = gitee_user['login']
                        avatar_url = gitee_user['avatar_url']
                        login_time = datetime.datetime.now()
                        try:
                            user = User.objects.get(gitee_id=gitee_id)
                            user.nickname = nickname
                            user.avatar_url = avatar_url
                            user.login_time = login_time
                            user.save()
                        except User.DoesNotExist:
                            uid = generate_uid()
                            user = User.objects.create(uid=uid, gitee_id=gitee_id,
                                                       avatar_url=avatar_url, nickname=nickname,
                                                       login_time=login_time)

                        if user:
                            token = generate_jwt(user.uid)
                            response.set_cookie(settings.JWT_COOKIE_KEY, token, domain=settings.COOKIE_DOMAIN)

    return response


@api_view()
def baidu(request):
    response = redirect(settings.RESIUM_UI)

    code = request.GET.get('code', None)
    if code:
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': settings.BAIDU_CLIENT_ID,
            'client_secret': settings.BAIDU_CLIENT_SECRET,
            'redirect_uri': settings.BAIDU_REDIRECT_URI  # 前后端都不要urlencode，否则会报错：回调地址不正确
        }
        with requests.get('https://openapi.baidu.com/oauth/2.0/token', params=params) as get_access_token_resp:
            if get_access_token_resp.status_code == requests.codes.OK:
                access_token = get_access_token_resp.json().get('access_token', None)
                if access_token:
                    params = {
                        'access_token': access_token
                    }
                    with requests.get('https://openapi.baidu.com/rest/2.0/passport/users/getInfo', params=params) as get_user_resp:
                        if get_user_resp.status_code == requests.codes.OK:
                            baidu_user = get_user_resp.json()
                            baidu_openid = baidu_user.get('openid', None)
                            if baidu_openid:  # 表示获取信息成功
                                login_time = datetime.datetime.now()
                                nickname = baidu_user['username']
                                avatar_url = f'http://tb.himg.baidu.com/sys/portrait/item/{baidu_user["portrait"]}'
                                try:
                                    user = User.objects.get(baidu_openid=baidu_openid)
                                    user.nickname = nickname
                                    user.avatar_url = avatar_url
                                    user.login_time = login_time
                                    user.save()
                                except User.DoesNotExist:
                                    uid = generate_uid()
                                    user = User.objects.create(uid=uid, baidu_openid=baidu_openid,
                                                               nickname=nickname, avatar_url=avatar_url,
                                                               login_time=login_time)

                                if user:
                                    token = generate_jwt(user.uid)
                                    response.set_cookie(settings.JWT_COOKIE_KEY, token, domain=settings.COOKIE_DOMAIN)

    return response


@api_view()
def dingtalk(request):
    response = redirect(settings.RESIUM_UI)

    code = request.GET.get('code', None)
    if code:
        timestamp = str(time.time()).replace('.', '')[:-3]
        params = {
            'accessKey': settings.DINGTALK_APP_ID,
            'timestamp': timestamp,
            'signature': get_ding_talk_signature(settings.DINGTALK_APP_SECRET, timestamp)
        }
        payload = {
            'tmp_auth_code': code
        }
        with requests.post('https://oapi.dingtalk.com/sns/getuserinfo_bycode', data=payload, params=params) as get_user_resp:
            if get_user_resp.status_code == requests.codes.OK and get_user_resp.json()['errcode'] == 0:
                dingtalk_user = get_user_resp.json()['user_info']
                dingtalk_openid = dingtalk_user['openid']
                nickname = dingtalk_user['nick']
                login_time = datetime.datetime.now()
                avatar_url = 'https://gw.alicdn.com/tfs/TB1H1qBb7yWBuNjy0FpXXassXXa-300-300.png'
                try:
                    user = User.objects.get(dingtalk_openid=dingtalk_openid)
                    user.nickname = nickname
                    user.login_time = login_time
                    user.save()
                except User.DoesNotExist:
                    uid = generate_uid()
                    user = User.objects.create(uid=uid, dingtalk_openid=dingtalk_openid,
                                               nickname=nickname, avatar_url=avatar_url,
                                               login_time=login_time)

                if user:
                    token = generate_jwt(user.uid)
                    response.set_cookie(settings.JWT_COOKIE_KEY, token, domain=settings.COOKIE_DOMAIN)

    return response
