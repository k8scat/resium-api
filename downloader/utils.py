# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import random
import re
import string
import time
import uuid
import zipfile
from json import JSONDecodeError
from urllib import parse

import alipay
import jwt
import oss2
import requests
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from oss2 import SizedFileAdapter, determine_part_size
from oss2.exceptions import NoSuchKey
from oss2.models import PartInfo
from qiniu import Auth, put_file, etag
from requests.exceptions import InvalidHeader
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from wechatpy import WeChatPay

from downloader.models import Resource, DownloadRecord, CsdnAccount, User


def ding(message, at_mobiles=None, is_at_all=False,
         error=None, uid='', download_account_id=None,
         resource_url='', logger=None,
         need_email=False, image=''):
    """
    使用钉钉Webhook Robot监控线上系统

    https://ding-doc.dingtalk.com/doc#/serverapi2/qf2nxq

    :param message:
    :param at_mobiles:
    :param is_at_all:
    :param error:
    :param uid:
    :param download_account_id:
    :param resource_url:
    :param logger:
    :param need_email:
    :param image:
    :return:
    """

    timestamp = round(time.time() * 1000)
    secret_enc = settings.DINGTALK_SECRET.encode('utf-8')
    string_to_sign = f'{timestamp}\n{settings.DINGTALK_SECRET}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = parse.quote_plus(base64.b64encode(hmac_code))

    if at_mobiles is None:
        at_mobiles = []

    content = f'## {message}\n' \
              f'- 错误信息：{str(error) if error else "无"}\n' \
              f'- 资源地址：{resource_url if resource_url else "无"}\n' \
              f'- 用户：{uid if uid else "无"}\n' \
              f'- 会员账号：{download_account_id if download_account_id else "无"}\n' \
              f'- 环境：{"开发环境" if settings.DEBUG else "生产环境"}\n' \
              f'{"![](" + image + ")" if image else ""}'

    if logger:
        logger(content)

    payload = {
        'msgtype': 'markdown',
        'markdown': {
            'title': message,
            'text': content
        },
        'at': {
            'atMobiles': at_mobiles,
            'isAtAll': is_at_all
        }
    }
    dingtalk_api = f'https://oapi.dingtalk.com/robot/send?access_token={settings.DINGTALK_ACCESS_TOKEN}&timestamp={timestamp}&sign={sign}'
    with requests.post(dingtalk_api, json=payload, verify=False) as r:
        logging.info(f'ding {r.status_code} {r.text}')

    if need_email:
        send_email(
            subject='[源自下载] 服务状态告警',
            content=content,
            to_addr=settings.ADMIN_EMAIL
        )


def get_aliyun_oss_bucket():
    # 阿里云主账号AccessKey拥有所有API的访问权限，风险很高。强烈建议您创建并使用RAM账号进行API访问或日常运维，请登录 https://ram.console.aliyun.com 创建RAM账号。
    auth = oss2.Auth(settings.ALIYUN_ACCESS_KEY_ID, settings.ALIYUN_ACCESS_KEY_SECRET)
    # Endpoint以杭州为例，其它Region请按实际情况填写。
    bucket = oss2.Bucket(auth, settings.ALIYUN_OSS_END_POINT, settings.ALIYUN_OSS_BUCKET_NAME)

    return bucket


def aliyun_oss_upload(filepath: str, key: str, use_print=False) -> bool:
    """
    阿里云 OSS 上传

    参考: https://help.aliyun.com/document_detail/88434.html?spm=a2c4g.11186623.6.849.de955fffeknceQ

    :param filepath: 文件路径
    :param key: 保存在oss上的文件名
    :return:
    """

    if use_print:
        print('正在上传资源...')
    else:
        logging.info('开始上传资源...')
    try:
        bucket = get_aliyun_oss_bucket()

        # 初始化分片。
        # 如果需要在初始化分片时设置文件存储类型，请在init_multipart_upload中设置相关headers，参考如下。
        # headers = dict()
        # headers["x-oss-storage-class"] = "Standard"
        # upload_id = bucket.init_multipart_upload(key, headers=headers).upload_id
        upload_id = bucket.init_multipart_upload(key).upload_id
        parts = []

        total_size = os.path.getsize(filepath)
        # determine_part_size方法用来确定分片大小。1000KB
        part_size = determine_part_size(total_size, preferred_size=1000 * 1024)

        # 逐个上传分片。
        with open(filepath, 'rb') as f:
            part_number = 1
            offset = 0
            while offset < total_size:
                # logging.info('Uploading')
                num_to_upload = min(part_size, total_size - offset)
                # SizedFileAdapter(f, size)方法会生成一个新的文件对象，重新计算起始追加位置。
                result = bucket.upload_part(key, upload_id, part_number,
                                            SizedFileAdapter(f, num_to_upload))
                parts.append(PartInfo(part_number, result.etag))
                offset += num_to_upload
                part_number += 1
                if use_print:
                    print(f"上传进度: {offset / total_size * 100}%")

            # 完成分片上传。
            # 如果需要在完成分片上传时设置文件访问权限ACL，请在complete_multipart_upload函数中设置相关headers，参考如下。
            # headers = dict()
            # headers["x-oss-object-acl"] = oss2.OBJECT_ACL_PRIVATE
            # bucket.complete_multipart_upload(key, upload_id, parts, headers=headers)
            bucket.complete_multipart_upload(key, upload_id, parts)
            return True

    except Exception as e:
        ding(f'资源({filepath})上传OSS失败，请检查OSS上传代码',
             error=e,
             logger=logging.error,
             need_email=True)
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
    try:
        return bucket.object_exists(key)
    except NoSuchKey:
        return None


def aliyun_oss_sign_url(key, expire=3600):
    """
    获取文件临时下载链接，使用签名URL进行临时授权

    参考: https://help.aliyun.com/document_detail/32033.html?spm=a2c4g.11186623.6.881.603f16950kd10U

    :param key:
    :param expire: 默认60*60, 即1小时后过期
    :return:
    """

    bucket = get_aliyun_oss_bucket()
    return bucket.sign_url('GET', key, expire)


def get_alipay():
    """
    获取AliPay实例

    :return:
    """

    with open(settings.ALIPAY_APP_PRIVATE_KEY_FILE) as f:
        alipay_app_private_key_string = f.read()
    with open(settings.ALIPAY_PUBLIC_KEY_FILE) as f:
        alipay_public_key_string = f.read()

    return alipay.AliPay(
        appid=settings.ALIPAY_APP_ID,
        app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,  # the default notify path
        app_private_key_string=alipay_app_private_key_string,
        # alipay public key, do not use your own public key!
        alipay_public_key_string=alipay_public_key_string,
        sign_type="RSA2",  # RSA or RSA2
        debug=False  # False by default
    )


def check_oss(resource_url):
    """
    检查oss是否已存储资源

    :param resource_url:
    :return: Resource
    """

    try:
        resource = Resource.objects.get(url=resource_url, is_audited=1)
        # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
        # 如果oss上没有存储资源，则提醒管理员检查资源
        if not aliyun_oss_check_file(resource.key):
            resource.delete()
            ding(f'OSS资源未找到，请及时检查资源 {resource.key}',
                 need_email=True)
            return None
        return resource
    except Resource.DoesNotExist:
        return None


def check_download(folder):
    """
    判断文件是否下载完成

    :param folder:
    :return:
    """
    logging.info('下载开始...')
    start = time.time()
    # 预计5分钟内下载完成
    no_file_countdown = 100
    for i in range(3000):
        files = os.listdir(folder)
        # 判断是否存在文件，一般来说，开始下载后会立即有.crdownload文件，如果在循环10次后还是没有的话，直接返回None
        if len(files) == 0:
            if no_file_countdown >= 0:
                no_file_countdown -= 1
                time.sleep(1)
                continue
            else:
                return 500, '检查下载文件不存在'
        elif files[0].endswith('.crdownload'):
            time.sleep(0.1)
            continue
        else:
            end = time.time()
            logging.info(f'下载成功, 耗时 {end - start} 秒')
            break

    else:
        ding(f'下载超时: {folder}',
             logger=logging.error,
             need_email=True)
        return 500, '检查下载文件超时'

    # 下载完成后，文件夹下存在唯一的文件
    filename = files[0]
    return 200, filename


def get_driver(folder='', load_images=False):
    """
    获取driver

    :param folder: 唯一文件夹
    :param load_images: 是否加载图片
    :return: WebDriver
    """
    options = webdriver.ChromeOptions()
    prefs = {
        "download.prompt_for_download": False,
        'download.default_directory': '/download/' + folder,  # 下载目录, 需要在docker做映射
        "plugins.always_open_pdf_externally": True,
        'profile.default_content_settings.popups': 0,  # 设置为0，禁止弹出窗口
    }
    # 禁止图片加载
    if not load_images:
        prefs.setdefault('profile.default_content_setting_values.images', 2)
    options.add_experimental_option('prefs', prefs)

    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps,
                              options=options)

    return driver


def save_resource(resource_url, filename, filepath,
                  resource_info, user, account_id=None,
                  return_url=False):
    """
    保存资源记录并上传到OSS

    :param resource_url:
    :param filename:
    :param filepath:
    :param resource_info:
    :param user: 下载资源的用户
    :param account_id: 使用的会员账号
    :param return_url:
    :return:
    """

    with open(filepath, 'rb') as f:
        file_md5 = get_file_md5(f)

    # 存储在oss中的key
    key = str(uuid.uuid1()) + os.path.splitext(filename)[1]
    upload_success = aliyun_oss_upload(filepath, key)
    if not upload_success:
        return None

    try:
        # 资源文件大小
        size = os.path.getsize(filepath)
        # django的CharField可以直接保存list，会自动转成str
        resource = Resource.objects.create(title=resource_info['title'], filename=filename, size=size,
                                           url=resource_url, key=key, tags=settings.TAG_SEP.join(resource_info['tags']),
                                           file_md5=file_md5, desc=resource_info['desc'], user=user,
                                           wenku_type=resource_info.get('wenku_type', None),
                                           is_docer_vip_doc=resource_info.get('is_docer_vip_doc', False),
                                           local_path=filepath)
        DownloadRecord(user=user,
                       resource=resource,
                       account_id=account_id,
                       used_point=resource_info['point']).save()

        ding(f'资源保存成功: {resource_info["title"]}',
             uid=user.uid,
             resource_url=resource_url,
             download_account_id=account_id)

        # 上传资源到CSDN
        # t = Thread(target=upload_csdn_resource, args=(resource,))
        # t.start()

        if return_url:
            return aliyun_oss_sign_url(key)

    except Exception as e:
        ding(f'资源信息保存失败，但资源已上传至OSS：{key}',
             error=e,
             resource_url=resource_url,
             uid=user.uid,
             download_account_id=account_id,
             logger=logging.error,
             need_email=True)
        return None


def get_file_md5(f):
    """
    检查文件的完整性

    :param f:
    :return:
    """

    m = hashlib.md5()
    while True:
        data = f.read(1024)
        if not data:
            break
        m.update(data)
    return m.hexdigest()


def aliyun_oss_delete_files(keys: list):
    """
    批量删除OSS上的文件

    :param keys:
    :return:
    """

    bucket = get_aliyun_oss_bucket()
    # 批量删除3个文件。每次最多删除1000个文件。
    result = bucket.batch_delete_objects(keys)
    # 打印成功删除的文件名。
    print('\n'.join(result.deleted_keys))


def send_message(phone, code):
    """
    发送短信

    :param phone: 手机号
    :param code: 验证码
    :return:
    """
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    client = AcsClient(settings.ALIYUN_ACCESS_KEY_ID,
                       settings.ALIYUN_ACCESS_KEY_SECRET,
                       'cn-hangzhou')

    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2017-05-25')
    request.set_action_name('SendSms')

    request.add_query_param('RegionId', "cn-hangzhou")
    request.add_query_param('PhoneNumbers', phone)
    request.add_query_param('SignName', settings.ALIYUN_SMS_SIGN_NAME)
    request.add_query_param('TemplateCode', settings.ALIYUN_SMS_TEMPLATE_CODE)
    request.add_query_param('TemplateParam', {
        'code': code
    })

    if settings.DEBUG:
        ding(code)
        return True
    try:
        client.do_action_with_exception(request)
        return True
    except Exception as e:
        logging.error(e)
        ding(f'短信验证码发送失败: {str(e)}',
             need_email=True)
        return False


def send_email(subject, content, to_addr):
    send_mail(
        subject,
        content,
        settings.DEFAULT_FROM_EMAIL,
        [to_addr],
        fail_silently=False,
    )


def aliyun_oss_delete_file(key):
    bucket = get_aliyun_oss_bucket()

    # 删除文件。<yourObjectName>表示删除OSS文件时需要指定包含文件后缀在内的完整路径，例如abc/efg/123.jpg。
    # 如需删除文件夹，请将<yourObjectName>设置为对应的文件夹名称。如果文件夹非空，则需要将文件夹下的所有object删除后才能删除该文件夹。
    bucket.delete_object(key)


def get_sign(pd_id, pd_key, timestamp):
    md5 = hashlib.md5()
    md5.update((timestamp + pd_key).encode())
    csign = md5.hexdigest()

    md5 = hashlib.md5()
    md5.update((pd_id + timestamp + csign).encode())
    csign = md5.hexdigest()
    return csign


def predict_code(image_path):
    """
    验证码识别

    :param image_path:
    :return:
    """

    tm = str(int(time.time()))
    sign = get_sign(settings.PD_ID, settings.PD_KEY, tm)
    data = {
        'user_id': settings.PD_ID,
        'timestamp': tm,
        'sign': sign,
        'predict_type': 30400,
        'up_type': 'mt'
    }
    url = 'http://pred.fateadm.com/api/capreg'
    files = {
        'img_data': ('img_data', open(image_path, 'rb').read())
    }
    headers = {
        'user-agent': get_random_ua()
    }
    # requests POST a Multipart-Encoded File
    # https://requests.readthedocs.io/en/master/user/quickstart/#post-a-multipart-encoded-file
    with requests.post(url, data, files=files, headers=headers) as r:
        if r.status_code == requests.codes.OK:
            result = r.json()
            logging.info(result)
            if result['RetCode'] == '0':
                code = json.loads(result['RspData'])['result']
                key = get_unique_str() + '.' + os.path.basename(image_path).split('.')[-1]
                if qiniu_upload(settings.QINIU_OPEN_BUCKET, image_path, key):
                    image_url = qiniu_get_url(key)
                    ding(f'验证码识别成功: {code}', image=image_url)
                else:
                    ding(f'验证码识别成功: {code}',
                         error='七牛云上传图片失败',

                         need_email=True)
                return code
            ding(f'验证码识别失败: {r.content.decode()}',
                 need_email=True)
            return None
        ding(f'验证码识别请求失败: {r.status_code} {r.content.decode()}',
             need_email=True)
        return None


def get_random_ua():
    """
    随机获取User-Agent

    :return:
    """

    ua_list = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
        # Google Chrome
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/82.0.4083.0 Safari/537.36 Edg/82.0.456.0',
        # Microsoft Edge
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15',
        # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:74.0) Gecko/20100101 Firefox/74.0'  # Firefox
    ]
    return random.choice(ua_list)


def upload_csdn_resource(resource):
    if not re.match(settings.PATTERN_CSDN, resource.url):
        logging.info(f'开始上传资源到CSDN: {resource.url}')
        headers = {
            'cookie': CsdnAccount.objects.get(is_upload_account=True).cookies,
            'user-agent': get_random_ua(),
            'referer': 'https://download.csdn.net/upload',
            'origin': 'https://download.csdn.net',
        }
        # 将资源与其他文件进行压缩，获得到不同的MD5
        filepath = zip_file(resource.local_path)
        file_md5 = get_file_md5(open(filepath, 'rb'))
        title = resource.title + f"[{''.join(random.sample(string.digits + string.ascii_letters, 6))}]"
        tags = resource.tags.replace(settings.TAG_SEP, ',').split(',')
        if len(tags) > 5:
            tags = ','.join(tags[:5])
        elif len(tags) == 1 and tags[0] == '':
            # 存在没有tag的情况
            # ''.split(',') => ['']
            tags = '好资源'
        else:
            tags = ','.join(tags)

        if len(resource.desc) < 50:
            desc = '源自开发者，关注"源自开发者"公众号，每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享。 ' + resource.desc
        elif re.match(settings.PATTERN_DOCER, resource.url):
            desc = '源自开发者，关注"源自开发者"公众号，每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享。 '
        else:
            desc = '源自开发者，关注"源自开发者"公众号，每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享。 ' + resource.desc

        payload = {
            'fileMd5': file_md5,
            'sourceid': '',
            'file_title': title,
            'file_type': 4,
            'file_primary': 15,  # 课程资源
            'file_category': 15012,  # 专业指导
            'resource_score': 5,
            'file_tag': tags,
            'file_desc': desc,
            'cb_agree': True
        }
        # logging.info(payload)
        files = [
            ('user_file', open(filepath, 'rb'))
        ]
        with requests.post('https://download.csdn.net/upload', headers=headers, data=payload, files=files) as r:
            if r.status_code == requests.codes.OK:
                try:
                    resp = r.json()
                except JSONDecodeError:
                    ding('资源上传到CSDN失败',
                         error=r.text,
                         logger=logging.error,
                         need_email=True)

                if resp['code'] == 200:
                    # 上传成功
                    ding('资源上传到CSDN成功')
                else:
                    # 上传失败
                    ding('资源上传到CSDN失败',
                         error=resp,
                         logger=logging.error,
                         need_email=True)


def zip_file(filepath):
    """
    压缩文件夹

    :param filepath: 需要压缩的文件
    :return:
    """

    outfile = os.path.join(settings.DOWNLOAD_DIR, str(uuid.uuid1()) + '.zip')
    files = [filepath, os.path.join(settings.DOWNLOAD_DIR, '.gitkeep')]
    f = zipfile.ZipFile(outfile, 'w', zipfile.zlib.DEFLATED)
    for file in files:
        filename = os.path.basename(file)
        f.write(file, filename)
    f.close()
    return outfile


def get_short_url(url, long_term=False):
    """
    生成短网址

    https://dwz.cn/console/apidoc

    :param url:
    :param long_term
    :return:
    """

    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Token': settings.BAIDU_DWZ_TOKEN
    }
    body = {
        'Url': url,
        'TermOfValidity': 'long-term' if long_term else '1-year'
    }
    with requests.post('https://dwz.cn/admin/v2/create', data=json.dumps(body), headers=headers) as r:
        if r.status_code == requests.codes.OK and r.json()['Code'] == 0:
            return r.json()['ShortUrl']
        else:
            ding('[短网址] 生成失败',
                 error=r.text,
                 need_email=True)
            return None


def get_long_url(url):
    """
    还原短网址

    https://dwz.cn/console/apidoc

    :param url:
    :return:
    """

    headers = {
        'Content-Type': 'application/json',
        'Token': settings.BAIDU_DWZ_TOKEN
    }
    body = {
        'shortUrl': url
    }
    with requests.post('https://dwz.cn/admin/v2/query', data=json.dumps(body), headers=headers) as r:
        if r.status_code == requests.codes.OK and r.json()['Code'] == 0:
            return r.json()['LongUrl']
        else:
            ding('[短网址] 生成失败',
                 error=r.text,
                 need_email=True)
            return None


def generate_jwt(sub, expire_seconds=3600 * 24):
    """
    生成token

    :param sub:
    :param expire_seconds: 默认1天过期
    :return:
    """

    payload = {
        'sub': sub
    }
    if expire_seconds > 0:
        exp = datetime.datetime.utcnow() + datetime.timedelta(seconds=expire_seconds)
        payload.setdefault('exp', exp)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm='HS512').decode()


def get_ding_talk_signature(app_secret, utc_timestamp):
    """
    https://www.cnblogs.com/zepc007/p/12154253.html

    :param app_secret: 钉钉开发者文档创建的app密钥
    :param utc_timestamp: 官方文档中要签名的数据，单位是毫秒时间戳
    :return: 为所需要的签名值，此值为可逆的
    """

    digest = hmac.HMAC(key=app_secret.encode('utf8'),
                       msg=utc_timestamp.encode('utf8'),
                       digestmod=hmac._hashlib.sha256).digest()
    signature = base64.standard_b64encode(digest).decode('utf8')
    return signature


def switch_csdn_account(csdn_account, need_sms_validate=False):
    """
    切换到可用账号
    切换的原因：
    1. 账号需要短信验证
    2. 账号cookies失效
    3. 账号可用下载数用完

    :param csdn_account:
    :param need_sms_validate:
    :return:
    """

    valid_admin_csdn_accounts = CsdnAccount.objects.filter(is_enabled=False,
                                                           today_download_count__lt=20,
                                                           need_sms_validate=False,
                                                           is_disabled=False,
                                                           csdn_id__in=settings.ADMIN_CSDN_ACCOUNTS).all()

    valid_csdn_accounts = CsdnAccount.objects.filter(is_enabled=False,
                                                     today_download_count__lt=20,
                                                     need_sms_validate=False,
                                                     is_disabled=False).all()
    if len(valid_csdn_accounts) > 0:
        # 随机开启一个可用账号，并尽可能使用管理员的CSDN账号
        if len(valid_admin_csdn_accounts) > 0:
            new_csdn_account = random.choice(valid_admin_csdn_accounts)
        else:
            new_csdn_account = random.choice(valid_csdn_accounts)
        new_csdn_account.is_enabled = True
        new_csdn_account.save()
        # 停止账号使用
        csdn_account.need_sms_validate = need_sms_validate
        csdn_account.is_enabled = False
        if not need_sms_validate:
            # 禁用账号
            csdn_account.is_disabled = True
            valid_count = get_csdn_valid_count(csdn_account.cookies)
            if valid_count is None:
                msg = f'CSDN会员账号（ID为{csdn_account.csdn_id}）的Cookies已失效，为了保障会员账号的可用性，请及时登录网站（https://resium.cn/user）进行重新设置Cookies，如有疑问请联系管理员！'
                send_email(
                    subject='[源自下载] CSDN账号提醒',
                    content=msg,
                    to_addr=csdn_account.user.email
                )
                feishu_send_message(text=msg, user_id=settings.FEISHU_USER_ID)
                ding('[CSDN] Cookies已失效',
                     download_account_id=csdn_account.id)
            elif valid_count == 0:
                csdn_account.is_disabled = True
                msg = f'CSDN会员账号（ID为{csdn_account.csdn_id}）的会员下载数已用尽，请知悉！'
                send_email(
                    subject='[源自下载] CSDN账号提醒',
                    content=msg,
                    to_addr=csdn_account.user.email
                )
                feishu_send_message(text=msg, user_id=settings.FEISHU_USER_ID)
        else:
            msg = f'CSDN会员账号（ID为{csdn_account.csdn_id}）需要进行短信验证，为了保障会员账号的可用性，请及时进行短信验证并登录网站（https://resium.cn/user）解除短信验证，如有疑问请联系管理员！【此消息来自定时任务，如已知悉请忽略】'
            send_email(
                subject='[源自下载] CSDN账号提醒',
                content=msg,
                to_addr=csdn_account.user.email
            )
            feishu_send_message(text=msg, user_id=settings.FEISHU_USER_ID)

        csdn_account.save()
        ding('[CSDN] 自动切换账号成功',
             download_account_id=csdn_account.id)
        return new_csdn_account
    else:
        csdn_account.need_sms_validate = need_sms_validate
        csdn_account.save()
        ding('[CSDN] 自动切换账号成功失败，没有可用的CSDN账号',
             download_account_id=csdn_account.id,
             need_email=True)
        return None


class WXBizDataCrypt:
    def __init__(self, app_id, session_key):
        self.app_id = app_id
        self.session_key = session_key

    def decrypt(self, encrypted_data, iv):
        # base64 decode
        session_key = base64.b64decode(self.session_key)
        encrypted_data = base64.b64decode(encrypted_data)
        iv = base64.b64decode(iv)

        cipher = AES.new(session_key, AES.MODE_CBC, iv)

        decrypted = json.loads(self._unpad(cipher.decrypt(encrypted_data)))

        try:
            app_id = decrypted['watermark']['appid']
            if app_id != self.app_id:
                ding(f'[小程序登录] wrong appid: {app_id}',
                     need_email=True)
                return None

            return decrypted
        except KeyError:
            ding('[小程序登录] decrypt KeyError',
                 need_email=True)
            return None

    def _unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]


def generate_uid(num=6):
    # 使用数字UID
    repetition_count = 0  # 计算重复次数
    uid = ''.join(random.sample(string.digits, num))
    while True:
        if User.objects.filter(uid=uid).count():
            repetition_count += 1
            uid = ''.join(random.sample(string.digits, num))
        else:
            if repetition_count > 0:
                ding(f'UID生成重复次数: {repetition_count}',
                     uid=uid,
                     need_email=True)
            return uid


def get_csdn_valid_count(cookies):
    """
    获取CSDN会员账号的可用下载数

    :param cookies:
    :return:
    """

    headers = {
        'cookie': cookies,
        'user-agent': get_random_ua()
    }
    try:
        with requests.get('https://download.csdn.net/my/vip', headers=headers) as r:
            soup = BeautifulSoup(r.text, 'lxml')
            el = soup.select('div.vip_info p:nth-of-type(1) span')
            try:
                return int(el[0].text)
            except Exception:
                return None
    except InvalidHeader:
        return None


def get_csdn_id(cookies):
    """
    获取CSDN账号ID

    :param cookies:
    :return:
    """

    try:
        headers = {
            'cookie': cookies,
            'user-agent': get_random_ua()
        }
        with requests.get('https://me.csdn.net/api/user/show', headers=headers) as r:
            resp = r.json()
            if resp['code'] == 200:
                return resp['data']['csdnid']
            else:
                return None
    except InvalidHeader:
        return None


def qiniu_upload(bucket, local_file, key):
    """
    七牛云存储上传文件

    :return:
    """

    q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = q.upload_token(bucket, key, 3600)
    ret, info = put_file(token, key, local_file)
    logging.info(info)
    return ret['key'] == key and ret['hash'] == etag(local_file)


def get_unique_str():
    """
    通过uuid获取唯一字符串

    :return:
    """

    return str(uuid.uuid1()).replace('-', '')


def qiniu_get_url(key):
    return 'http://' + settings.QINIU_OPEN_DOMAIN + '/' + key


def get_we_chat_pay():
    return WeChatPay(
        appid=settings.WX_PAY_MP_APP_ID,
        mch_key=settings.WX_PAY_MCH_KEY,
        mch_cert=settings.WX_PAY_MCH_CERT,
        sub_appid=settings.WX_PAY_SUB_APP_ID,
        api_key=settings.WX_PAY_API_KEY,
        mch_id=settings.WX_PAY_MCH_ID
    )


def get_wenku_doc_id(url):
    # https://wenku.baidu.com/view/e414fc173a3567ec102de2bd960590c69ec3d8f8.html?fr=search_income2
    doc_id = url.split('?')[0].split('baidu.com/view/')[1]
    if doc_id.count('.') > 0:
        doc_id = doc_id.split('.')[0]
    url = 'https://wenku.baidu.com/view/' + doc_id + '.html'
    return url, doc_id


def get_random_int(num=6):
    return ''.join(random.sample(string.digits, num))


class AESCipher(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def decrypt(self, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return self.decrypt(enc).decode('utf8')


def feishu_verify_decrypt(encrypt):
    cipher = AESCipher(settings.FEISHU_APP_ENCRYPT_KEY)
    try:
        decrypt_string = cipher.decrypt_string(encrypt)
        return json.loads(decrypt_string)
    except UnicodeDecodeError:
        return None


def feishu_get_tenant_access_token():
    token = cache.get('feishu_token')
    if token:
        return token
    else:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        payload = {
            'app_id': settings.FEISHU_APP_ID,
            'app_secret': settings.FEISHU_APP_SECRET
        }
        with requests.post(url, json=payload) as r:
            if r.status_code == requests.codes.ok:
                data = r.json()
                if data.get('code', -1) == 0:
                    token = data.get('tenant_access_token', None)
                    if token:
                        cache.set('feishu_token', token, timeout=settings.DOWNLOAD_INTERVAL)
                        return token
                    else:
                        ding(message='[飞书] access_token获取失败',
                             error=data['msg'],
                             logger=logging.error,
                             need_email=True)
                        return None
                else:
                    ding(message='[飞书] access_token获取失败',
                         error=data['msg'],
                         logger=logging.error,
                         need_email=True)
                    return None
            else:
                ding(message=f'[飞书] 接口请求失败, code={r.status_code}, content={str(r.content)}',
                     logger=logging.error,
                     need_email=True)
                return None


def feishu_send_message(text, chat_id=None, open_id=None, user_id=None, email=None, root_id=None):
    if not chat_id and not open_id and not user_id and not email:
        return

    logging.info(f'[feishu] send message: {text}')

    url = "https://open.feishu.cn/open-apis/message/v4/send/"
    token = feishu_get_tenant_access_token()
    headers = {
        "Authorization": "Bearer " + token
    }
    data = {
        'msg_type': 'text',
        'content': {
            'text': text
        }
    }
    if chat_id:
        data['chat_id'] = chat_id
    if open_id:
        data['open_id'] = open_id
    if user_id:
        data['user_id'] = user_id
    if email:
        data['email'] = email
    if root_id:
        data['root_id'] = root_id
    with requests.post(url, json=data, headers=headers) as r:
        resp_data = r.json()
        if resp_data.get('code', -1) != 0:
            ding('[feishu] 消息发送失败',
                 error=resp_data.get('msg', ''),
                 logger=logging.error,
                 need_email=True)


def random_weight(data_map):
    data_list = []
    for k, num in data_map.items():
        data_list.extend([k] * num)
    return random.choice(data_list)
