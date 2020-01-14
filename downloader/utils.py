# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import json
import logging

import requests
from django.conf import settings
from django.utils import timezone
from qiniu import Auth, put_data


def ding(content, at_mobiles=None, is_at_all=False):
    if at_mobiles is None:
        at_mobiles = ['17770040362']
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'msgtype': 'text',
        'text': {
            'content': 'CSDNBot: ' + content + ' at ' + str(timezone.now())
        },
        'at': {
            'atMobiles': at_mobiles,
            'isAtAll': is_at_all
        }
    }
    requests.post(settings.DINGTALK_API, data=json.dumps(data), headers=headers)


def qiniu_upload(file, key):
    """七牛云上传文件

    :param file: 文件路径（绝对路径或者相对路径）
    :param key: 上传文件名
    :return bool: 是否上传成功
    """
    try:
        q = Auth(settings.QINIU_AK, settings.QINIU_SK)
        token = q.upload_token(settings.QINIU_BUCKET, key)
        ret, info = put_data(token, key, file)
        if info.status_code == 200:
            logging.info(info)
            return True
        else:
            logging.error(info)
            return False
    except Exception as e:
        logging.error(e)
        return False


