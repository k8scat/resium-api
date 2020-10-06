# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/8/9

"""
import json
import logging
import re

import requests
from django.conf import settings
from django.http import JsonResponse
from django.http.response import HttpResponse
from rest_framework.decorators import api_view

from downloader import utils
from downloader.models import CsdnAccount, User
from downloader.serializers import CsdnAccountSerializers, UserSerializers
from downloader.utils import ding


@api_view(['POST'])
def bot(request):
    encrypt = request.data.get('encrypt', '')
    data = utils.feishu_verify_decrypt(encrypt)
    if data:
        token = data.get('token', '')
        # 验证事件来源
        if token == settings.FEISHU_APP_VERIFICATION_TOKEN:
            # 事件类型
            feishu_request_type = data.get('type', '')
            if feishu_request_type == 'url_verification':
                challenge = data.get('challenge', '')
                logging.info('challenge: ' + challenge)
                return JsonResponse(dict(challenge=challenge))

            elif feishu_request_type == 'event_callback':
                # 获取事件内容和类型，并进行相应处理，此处只关注给机器人推送的消息事件
                event = data.get('event')
                if event.get('type', '') == 'message':
                    # 此处只处理 text 类型消息，其他类型消息忽略
                    msg_type = event.get('msg_type', '')
                    if msg_type == 'text':
                        content = ''
                        msg_content = event.get('text_without_at_bot', '')
                        if re.match(r'^qc$', msg_content, flags=re.IGNORECASE):  # 查看CSDN账号
                            content = list_csdn_accounts()

                        elif re.match(r'^q \d{6}$', msg_content, flags=re.IGNORECASE):  # 查看用户信息
                            uid = msg_content.split(' ')[1]
                            content = get_user(uid)


                        elif re.match(r'^\d{6}$', msg_content):  # 激活该账号的下载功能
                            uid = msg_content
                            content = set_user_can_download(uid)

                        elif re.match(r'^tb \d{6}$', msg_content, flags=re.IGNORECASE):  # 激活淘宝账号的下载功能
                            uid = msg_content.split(' ')[1]
                            content = activate_taobao_user(uid)

                        elif re.match(r'^help$', msg_content, flags=re.IGNORECASE):
                            content = '1. 查看账号: q ID\n' \
                                      '2. 授权账号: ID\n' \
                                      '3. (取消)禁言: (n)b\n' \
                                      '4. 查看CSDN账号: qc\n' \
                                      '5. 淘宝用户授权: tb ID'

                        utils.feishu_send_message(content, user_id=settings.FEISHU_USER_ID)
        else:
            ding(message='feishu verification token not match, token = ' + token,
                 logger=logging.warning)

    return HttpResponse('')


def set_user_can_download(uid):
    try:
        user = User.objects.get(uid=uid)
        if user.can_download:
            return '该账号已开启外站资源下载功能'

        user.can_download = True
        user.save()
        return '成功设置用户可下载外站资源'
    except User.DoesNotExist:
        return '用户不存在'


def get_user(uid):
    try:
        user = User.objects.get(uid=uid)
        return json.dumps(UserSerializers(user).data)
    except User.DoesNotExist:
        return '用户不存在'


def set_csdn_sms_validate_code(email, code):
    try:
        account = CsdnAccount.objects.get(email=email, need_sms_validate=True)
        account.sms_code = code
        account.save()

        return '验证码保存成功'
    except User.DoesNotExist:
        return '账号不存在'

def list_csdn_accounts():
    """
    获取csdn账号信息

    :return:
    """

    content = ''
    accounts = CsdnAccount.objects.all()

    for index, account in enumerate(accounts):
        content += json.dumps(CsdnAccountSerializers(account).data)
        if index < len(accounts) - 1:
            content += '\n\n'
    return content

def activate_taobao_user(uid):
    try:
        user = User.objects.get(uid=uid)
        if user.can_download:
            return '淘宝用户或者源自用户只能购买一次'
        user.point += 10
        user.can_download = True
        user.from_taobao = True
        user.save()
        return '成功授权并发放积分'
    except User.DoesNotExist:
        return '用户不存在'

def send_msg(user_id, content):
    api = 'https://open.feishu.cn/open-apis/message/v4/send/'
    token = get_access_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'user_id': user_id,
        'msg_type': 'text',
        'content': {
            'text': content
        }
    }
    with requests.post(api, json=payload, headers=headers) as r:
        data = r.json()
        if data.get('code', '') != 0:
            logging.error(data['msg'])
