# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/8/9

"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.http.response import HttpResponseBase
from rest_framework.decorators import api_view

from downloader import utils
from downloader.utils import ding


@api_view(['POST'])
def bot(request):
    encrypt = request.data.get('encrypt', '')
    data = utils.feishu_verify_decrypt(encrypt)
    logging.info(type(data))
    if data:
        token = data.get('token', '')
        if token == settings.FEISHU_APP_VERIFICATION_TOKEN:
            feishu_request_type = data.get('type', '')
            if feishu_request_type == 'url_verification':
                challenge = data.get('challenge', '')
                logging.info('challenge: ' + challenge)
                return JsonResponse(dict(challenge=challenge))

            elif feishu_request_type == 'event_callback':
                # 获取事件内容和类型，并进行相应处理，此处只关注给机器人推送的消息事件
                event = data.get("event")
                if event.get("type", "") == "message":
                    # 此处只处理 text 类型消息，其他类型消息忽略
                    msg_type = event.get("msg_type", "")
                    if msg_type != "text":
                        return HttpResponseBase()

                    # 调用发消息 API 之前，先要获取 API 调用凭证：tenant_access_token
                    access_token = utils.feishu_get_tenant_access_token()
                    if not access_token:
                        return HttpResponseBase()

                    # 机器人 echo 收到的消息
                    utils.feishu_send_message(access_token, event.get("open_id"), 'Got!')
                    return HttpResponseBase()
        else:
            ding(message='feishu verification token not match, token = ' + token,
                 logger=logging.warning)
            return HttpResponseBase()
    else:
        return HttpResponseBase()
