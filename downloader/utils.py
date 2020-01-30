# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import json
import logging

import requests
from django.conf import settings

import os
from oss2 import SizedFileAdapter, determine_part_size
from oss2.models import PartInfo
import oss2
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def ding(content, at_mobiles=None, is_at_all=False):
    if at_mobiles is None:
        at_mobiles = ['17770040362']
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'msgtype': 'text',
        'text': {
            'content': 'CSDNBot: ' + content
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
                logging.info('Uploading')
                num_to_upload = min(part_size, total_size - offset)
                # SizedFileAdapter(fileobj, size)方法会生成一个新的文件对象，重新计算起始追加位置。
                result = bucket.upload_part(key, upload_id, part_number,
                                            SizedFileAdapter(fileobj, num_to_upload))
                parts.append(PartInfo(part_number, result.etag))

                offset += num_to_upload
                part_number += 1

        logging.info('Upload ok')

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


def aliyun_oss_check_file(key):
    """
    判断文件是否存在

    参考: https://help.aliyun.com/document_detail/88454.html?spm=a2c4g.11186623.6.861.321b3557YkGK3S

    :param key:
    :return:
    """
    bucket = get_aliyun_oss_bucket()
    return bucket.object_exists(key)


def aliyun_oss_sign_url(key):
    """
    获取文件临时下载链接，使用签名URL进行临时授权

    参考: https://help.aliyun.com/document_detail/32033.html?spm=a2c4g.11186623.6.881.603f16950kd10U

    :param key:
    :return:
    """

    bucket = get_aliyun_oss_bucket()
    return bucket.sign_url('GET', key, 60 * 60)


def csdn_auto_login():
    csdn_github_oauth_url = 'https://github.com/login?client_id=4bceac0b4d39cf045157&return_to=%2Flogin%2Foauth%2Fauthorize%3Fclient_id%3D4bceac0b4d39cf045157%26redirect_uri%3Dhttps%253A%252F%252Fpassport.csdn.net%252Faccount%252Flogin%253FpcAuthType%253Dgithub%2526state%253Dtest'
    github_login_url = 'https://github.com/login'

    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps)
    try:
        # 登录GitHub
        driver.get(github_login_url)

        login_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'login_field'))
        )
        login_field.send_keys(settings.GITHUB_USERNAME)

        password = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'password'))
        )
        password.send_keys(settings.GITHUB_PASSWORD)

        password.send_keys(Keys.ENTER)

        driver.get(csdn_github_oauth_url)

        cookies = driver.get_cookies()

        for c in cookies:
            if c['value'] == 'ken1583096683':
                # 登录成功则保存cookies
                cookies_str = json.dumps(cookies)
                with open(settings.CSDN_COOKIES_FILE, 'w') as f:
                    f.write(cookies_str)
                ding('cookies更新成功')
                return True

        ding('cookies更新失败，请检查CSDN自动登录脚本')
        return False

    except Exception as e:
        logging.error(e)
        ding('CSDN自动登录出现异常 ' + str(e))
        return False

    finally:
        driver.close()
