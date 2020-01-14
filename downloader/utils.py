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

import os
from oss2 import SizedFileAdapter, determine_part_size
from oss2.models import PartInfo
import oss2


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


def get_aliyun_oss_bucket():
    # 阿里云主账号AccessKey拥有所有API的访问权限，风险很高。强烈建议您创建并使用RAM账号进行API访问或日常运维，请登录 https://ram.console.aliyun.com 创建RAM账号。
    auth = oss2.Auth(settings.ALIYUN_ACCESS_KEY_ID, settings.ALIYUN_ACCESS_KEY_SECRET)
    # Endpoint以杭州为例，其它Region请按实际情况填写。
    bucket = oss2.Bucket(auth, settings.ALIYUN_OSS_END_POINT, settings.ALIYUN_OSS_BUCKET_NAME)

    return bucket


def aliyun_oss_upload(file, key):
    """
    阿里云 OSS 上传

    参考: https://help.aliyun.com/document_detail/88434.html?spm=a2c4g.11186623.6.849.de955fffeknceQ

    :param file: 文件路径
    :param key: 保存在oss上的文件名
    :return:
    """

    try:
        bucket = get_aliyun_oss_bucket()

        total_size = os.path.getsize(file)
        # determine_part_size方法用来确定分片大小。100KB
        part_size = determine_part_size(total_size, preferred_size=100 * 1024)

        # 初始化分片。
        # 如果需要在初始化分片时设置文件存储类型，请在init_multipart_upload中设置相关headers，参考如下。
        # headers = dict()
        # headers["x-oss-storage-class"] = "Standard"
        # upload_id = bucket.init_multipart_upload(key, headers=headers).upload_id
        upload_id = bucket.init_multipart_upload(key).upload_id
        parts = []

        # 逐个上传分片。
        with open(file, 'rb') as fileobj:
            part_number = 1
            offset = 0
            while offset < total_size:
                num_to_upload = min(part_size, total_size - offset)
                # SizedFileAdapter(fileobj, size)方法会生成一个新的文件对象，重新计算起始追加位置。
                result = bucket.upload_part(key, upload_id, part_number,
                                            SizedFileAdapter(fileobj, num_to_upload))
                parts.append(PartInfo(part_number, result.etag))

                offset += num_to_upload
                part_number += 1

        # 完成分片上传。
        # 如果需要在完成分片上传时设置文件访问权限ACL，请在complete_multipart_upload函数中设置相关headers，参考如下。
        # headers = dict()
        # headers["x-oss-object-acl"] = oss2.OBJECT_ACL_PRIVATE
        # bucket.complete_multipart_upload(key, upload_id, parts, headers=headers)
        bucket.complete_multipart_upload(key, upload_id, parts)

        # 验证分片上传。
        with open(file, 'rb') as fileobj:
            return bucket.get_object(key).read() == fileobj.read()

    except Exception as e:
        logging.error(e)
        return False


def aliyun_oss_get_file(key):
    """
    获取阿里云 OSS 上的文件
    bucket.get_object的返回值是一个类文件对象（File-Like Object）

    参考: https://help.aliyun.com/document_detail/88441.html?spm=a2c4g.11186623.6.854.252f6beeASG3vx

    :param key:
    :return: 类文件对象（File-Like Object）
    """

    bucket = get_aliyun_oss_bucket()
    return bucket.get_object(key)
