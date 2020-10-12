# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/8/9

"""
import base64
import json
import logging
import os
import re
import uuid

import requests
from django.conf import settings
from django.http import JsonResponse
from django.http.response import HttpResponse
from rest_framework.decorators import api_view

from downloader import utils
from downloader.apis.resource import CsdnResource, WenkuResource
from downloader.models import CsdnAccount, User, Resource
from downloader.serializers import CsdnAccountSerializers, UserSerializers
from downloader.utils import ding, save_resource, get_wenku_doc_id, feishu_get_tenant_access_token


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
                    msg_type = event.get('msg_type', '')
                    if msg_type == 'text':
                        msg_content = event.get('text_without_at_bot', '')
                        logging.info(f'[feishu] msg_content={msg_content}')
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

                        elif re.match(r'^[a-z0-9-_]* .*$', msg_content) or \
                                re.match(r'^http://cdn\.qiniu\.ncucoder\.com/.* .*', msg_content):  # 上传CSDN资源
                            utils.feishu_send_message('正在上传...', user_id=settings.FEISHU_USER_ID)
                            parts = msg_content.split(' ')
                            part1 = parts[0]
                            url = parts[1]
                            if re.match(r'^http://cdn\.qiniu\.ncucoder\.com/.*$', part1):
                                content = upload_csdn(url, download_url=part1)
                            elif re.match(r'^[a-z0-9-_]*$', part1):
                                content = upload_csdn(url, feishu_file_key=part1)
                            else:
                                content = f'part1 not matched, part1={part1}'

                        # 检查资源是否存在
                        elif re.match(settings.PATTERN_CSDN, msg_content):
                            url = msg_content
                            if Resource.objects.filter(url=url).count() == 0:
                                content = '资源不存在'
                            else:
                                content = '资源已存在'

                        elif re.match(r'^help$', msg_content, flags=re.IGNORECASE):
                            content = '1. 查看账号: q ID\n' \
                                      '2. 授权账号: ID\n' \
                                      '3. 查看CSDN账号: qc\n' \
                                      '4. 淘宝用户授权: tb ID\n' \
                                      '5. 上传CSDN/WENKU资源: file_key url' \
                                      '6. 检查CSDN资源是否存在: csdn_url' \
                                      '7. 帮助说明: help'
                        else:
                            content = None

                    elif msg_type == 'file':
                        file_key = event.get('file_key', None)
                        content = file_key

                    else:
                        content = f'暂不支持该消息类型: {msg_type}'

                    if content:
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


def upload_csdn(url, feishu_file_key=None, download_url=None):
    if not feishu_file_key and not download_url:
        return 'upload_csdn needs param feishu_file_key or download_url'

    # 生成资源存放的唯一子目录
    unique_folder = str(uuid.uuid1())
    save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
    while True:
        if os.path.exists(save_dir):
            unique_folder = str(uuid.uuid1())
            save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
        else:
            os.mkdir(save_dir)
            break

    if feishu_file_key:
        api = 'https://open.feishu.cn/open-apis/open-file/v1/get'
        params = {
            'file_key': feishu_file_key
        }
        token = feishu_get_tenant_access_token()
        headers = {
            "Authorization": "Bearer " + token
        }
        with requests.get(api, params=params, headers=headers, stream=True) as r:
            if r.status_code == requests.codes.OK:
                content_disposition = r.headers.get('content-disposition', None)
                if content_disposition:
                    # attachment; filename="wx_camera_1601781948017.mp4"
                    logging.info(f'[feishu] content-disposition={r.headers["content-disposition"]}')

                    filename = content_disposition.split('"')[1]
                    file = os.path.splitext(filename)
                    filename_uuid = str(uuid.uuid1()) + file[1]
                    filepath = os.path.join(save_dir, filename_uuid)
                else:
                    return '上传失败, content-disposition不存在'

                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
            else:
                return f'文件获取接口请求失败, code={r.status_code}, content={str(r.content)}'

    elif download_url:
        with requests.get(download_url, stream=True) as r:
            if r.status_code == requests.codes.OK:
                filename = download_url.split('/')[-1]
                file = os.path.splitext(filename)
                filename_uuid = str(uuid.uuid1()) + file[1]
                filepath = os.path.join(save_dir, filename_uuid)

                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
            else:
                return f'文件获取接口请求失败, code={r.status_code}, content={str(r.content)}'

    user = User.objects.get(uid='666666')
    if Resource.objects.filter(url=url).count() == 0:
        if re.match(settings.PATTERN_CSDN, url):
            resource = CsdnResource(url, user)
        elif re.match(settings.PATTERN_WENKU, url):
            url, doc_id = get_wenku_doc_id(url)
            resource = WenkuResource(url, user, doc_id)
        else:
            return f'无效的url, url={url}'

        status, resource_info = resource.parse()
        if status == requests.codes.ok:
            result = save_resource(url, filename, filepath,
                                   resource_info, user, return_url=True)
            if result:
                return '资源上传阿里云OSS成功'
            else:
                return '资源上传阿里云OSS失败'
        else:
            return resource_info
    else:
        return '资源已存在'
