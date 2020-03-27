# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import base64
import hashlib
import hmac
import json
import logging
import random
import string
import time
import uuid
import zipfile
from json import JSONDecodeError
from threading import Thread
from urllib import parse

import alipay
import requests
from django.conf import settings

import os

from django.core.mail import send_mail
from django.db.models import Q
from oss2 import SizedFileAdapter, determine_part_size
from oss2.exceptions import NoSuchKey
from oss2.models import PartInfo
import oss2
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from downloader.models import Resource, DownloadRecord, CsdnAccount, BaiduAccount, Coupon


def ding(message, at_mobiles=None, is_at_all=False,
         error=None, user_email='', used_account='',
         resource_url='', logger=logging.info, qq=None):
    """
    使用钉钉Webhook Robot监控线上系统

    :param message:
    :param at_mobiles:
    :param is_at_all:
    :param error:
    :param user_email:
    :param used_account:
    :param resource_url:
    :param logger:
    :param qq:
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
    headers = {
        'Content-Type': 'application/json'
    }
    content = f'## {message}\n' \
              f'- 错误信息：{str(error) if error else "无"}\n' \
              f'- 资源地址：{resource_url if resource_url else "无"}\n' \
              f'- 用户邮箱：{user_email if user_email else "无"}\n' \
              f'- 会员账号：{used_account if used_account else "无"}\n' \
              f'- QQ：{str(qq) if qq else "无"}' \
              f'- 环境：{"开发环境" if settings.DEBUG else "生产环境"}'
    logger(content)

    data = {
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
    requests.post(dingtalk_api, data=json.dumps(data), headers=headers)


def get_aliyun_oss_bucket():
    # 阿里云主账号AccessKey拥有所有API的访问权限，风险很高。强烈建议您创建并使用RAM账号进行API访问或日常运维，请登录 https://ram.console.aliyun.com 创建RAM账号。
    auth = oss2.Auth(settings.ALIYUN_ACCESS_KEY_ID, settings.ALIYUN_ACCESS_KEY_SECRET)
    # Endpoint以杭州为例，其它Region请按实际情况填写。
    bucket = oss2.Bucket(auth, settings.ALIYUN_OSS_END_POINT, settings.ALIYUN_OSS_BUCKET_NAME)

    return bucket


def aliyun_oss_upload(filepath: str, key: str) -> bool:
    """
    阿里云 OSS 上传

    参考: https://help.aliyun.com/document_detail/88434.html?spm=a2c4g.11186623.6.849.de955fffeknceQ

    :param filepath: 文件路径
    :param key: 保存在oss上的文件名
    :return:
    """
    logging.info('开始上传资源...')
    start = time.time()
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

            # 完成分片上传。
            # 如果需要在完成分片上传时设置文件访问权限ACL，请在complete_multipart_upload函数中设置相关headers，参考如下。
            # headers = dict()
            # headers["x-oss-object-acl"] = oss2.OBJECT_ACL_PRIVATE
            # bucket.complete_multipart_upload(key, upload_id, parts, headers=headers)
            bucket.complete_multipart_upload(key, upload_id, parts)

            end = time.time()

        with open(filepath, 'rb') as file:
            try:
                if bucket.get_object(key).read() == file.read():
                    logging.info(f'上传成功: {key}, 耗时 {end - start} 秒')
                    ding(f'资源成功上传OSS: {key}, 耗时{round(end-start, 2)}秒')
                    return True
                else:

                    return False
            except Exception as e:
                ding('资源上传OSS失败',
                     error=e,
                     logger=logging.error)
                return False
    except Exception as e:
        ding(f'资源({filepath})上传OSS失败，请检查OSS上传代码',
             error=e,
             logger=logging.error)
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
    :param expire: 默认10*60, 即10分钟后过期
    :return:
    """

    bucket = get_aliyun_oss_bucket()
    return bucket.sign_url('GET', key, expire)


def baidu_auto_login():
    """
    百度第一次登录必须手动登录并保存cookies
    自动登录是在已经验证异地登录的情况下进行的

    :return:
    """
    baidu_accounts = BaiduAccount.objects.all()
    for baidu_account in baidu_accounts:

        wenku_home = 'https://wenku.baidu.com/'
        logout = 'https://passport.baidu.com/?logout&aid=7&u=https%3A//login.bce.baidu.com/'

        cookies = json.loads(baidu_account.cookies)
        caps = DesiredCapabilities.CHROME
        driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps)

        try:
            driver.get(wenku_home)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                driver.add_cookie(cookie)

            # 再退出登录
            driver.get(logout)

            # 百度云登录用户名输入框
            username_input = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_4__userName'))
            )
            # 百度云登录密码输入框
            password_input = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_4__password'))
            )
            # 百度云登录按钮
            login_button = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_4__submit'))
            )

            username_input.send_keys(baidu_account.username)
            password_input.send_keys(baidu_account.password)
            login_button.click()
            # 等待跳转进百度云
            time.sleep(5)
            driver.get(wenku_home)

            try:
                # 尝试获取百度账号的昵称, 目前这个昵称是不能更改的
                nickname = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//a[@id='userNameCon']/span"))
                ).text.strip()
            except TimeoutException:
                nickname = None
            if nickname == baidu_account.nickname:
                # 保存cookies
                baidu_cookies = driver.get_cookies()
                baidu_cookies_str = json.dumps(baidu_cookies)
                # 保存cookies以及更新百度账号状态
                baidu_account.cookies = baidu_cookies_str
                baidu_account.save()
                ding(f'百度账号 {baidu_account.username} cookies 更新成功')
            else:
                ding(f'百度账号 {baidu_account.username} cookies更新失败, 请及时检查百度自动登录代码')
        except Exception as e:
            logging.error(e)
            ding(f'百度账号 {baidu_account.username} 自动登录出现异常 ' + str(e))
        finally:
            driver.close()


def csdn_auto_login():
    """
    CSDN自动登录
    自动登录是在已经验证异地登录的情况下进行的

    :return:
    """
    csdn_accounts = CsdnAccount.objects.all()
    for csdn_account in csdn_accounts:
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
            login_field.send_keys(csdn_account.github_username)

            password = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'password'))
            )
            password.send_keys(csdn_account.github_password)
            # 回车登录
            password.send_keys(Keys.ENTER)
            # GitHub OAuth 登录CSDN
            driver.get(csdn_github_oauth_url)
            # 获取csdn cookies
            csdn_cookies = driver.get_cookies()

            for cookie in csdn_cookies:
                if cookie['value'] == csdn_account.username:
                    # 登录成功则保存cookies
                    csdn_cookies_str = json.dumps(csdn_cookies)
                    # 保存cookies并更新账号状态
                    csdn_account.cookies = csdn_cookies_str
                    csdn_account.save()
                    ding(f'CSDN账号 {csdn_account.username} cookies更新成功')
                    break
            else:
                ding(f'CSDN账号 {csdn_account.username} cookies更新失败，请及时检查CSDN自动登录脚本')
        except Exception as e:
            logging.error(e)
            ding(f'CSDN账号 {csdn_account.username} 自动登录出现异常 ' + str(e))
        finally:
            driver.close()


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


def check_oss(resource_url, zhiwang_type=None):
    """
    检查oss是否已存储资源

    :param resource_url:
    :param zhiwang_type:
    :return: Resource
    """

    try:
        resource = Resource.objects.get(url=resource_url, is_audited=1, zhiwang_type=zhiwang_type)
        # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
        # 如果oss上没有存储资源，则提醒管理员检查资源
        if not aliyun_oss_check_file(resource.key):
            resource.is_audited = 0
            resource.save()
            ding(f'OSS资源未找到，请及时检查资源 {resource.key}')
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
                time.sleep(0.1)
                continue
            else:
                return None
        elif files[0].endswith('.crdownload'):
            time.sleep(0.1)
            continue
        else:
            end = time.time()
            logging.info(f'下载成功, 耗时 {end - start} 秒')
            break

    else:
        logging.error('下载失败: 下载超时')
        ding('下载失败: 下载超时')
        return None

    # 下载完成后，文件夹下存在唯一的文件
    filename = files[0]
    # 生成文件的绝对路径
    filepath = os.path.join(folder, filename)

    return filepath, filename


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
    # 线上使用selenium server
    driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps,
                              options=options)

    # 本地图形界面自动化测试
    # driver = webdriver.Chrome(options=options)
    return driver


def save_resource(resource_url, filename, filepath,
                  title, tags, desc, used_point, user,
                  account=None, wenku_type=None, zhiwang_type=None, is_docer_vip_doc=False, ret=False):
    """
    保存资源记录并上传到OSS

    :param resource_url:
    :param filename:
    :param filepath:
    :param title:
    :param tags:
    :param desc:
    :param used_point:
    :param user: 下载资源的用户
    :param account: 使用的会员账号
    :param wenku_type: 百度文库文档类型
    :param zhiwang_type: 知网文献类型，pdf/caj
    :param is_docer_vip_doc: 是否是稻壳VIP模板
    :param ret: 是否返回数据
    :return:
    """

    with open(filepath, 'rb') as f:
        file_md5 = get_file_md5(f)
    # 判断资源记录是否已存在，如果已存在则直接返回
    if Resource.objects.filter((Q(url=resource_url) & Q(zhiwang_type=zhiwang_type)) | Q(file_md5=file_md5)).count():
        return None

    # 存储在oss中的key
    key = str(uuid.uuid1()) + '-' + filename
    upload_success = aliyun_oss_upload(filepath, key)
    if not upload_success:
        return None

    try:
        # 资源文件大小
        size = os.path.getsize(filepath)
        resource = Resource.objects.create(title=title, filename=filename, size=size,
                                           url=resource_url, key=key, tags=tags,
                                           file_md5=file_md5, desc=desc, user_id=1,
                                           wenku_type=wenku_type, zhiwang_type=zhiwang_type,
                                           is_docer_vip_doc=is_docer_vip_doc, local_path=filepath)
        DownloadRecord(user=user,
                       resource=resource,
                       account=account.email if account else None,
                       download_device=user.login_device,
                       download_ip=user.login_ip,
                       used_point=used_point).save()

        ding(f'资源保存成功: {title}',
             user_email=user.email,
             resource_url=resource_url,
             used_account=account.email)

        # 如果资源小于200M，将资源上传到CSDN
        if size < 200 * 1000 * 100:
            t = Thread(target=upload_csdn_resource, args=(resource,))
            t.start()

        if ret:
            return aliyun_oss_sign_url(key)

    except Exception as e:
        ding(f'资源信息保存失败，但资源已上传至OSS：{key}',
             error=e,
             resource_url=resource_url,
             user_email=user.email,
             used_account=account.email,
             logger=logging.error)


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


def create_coupon(user, comment, total_amount=1.8, point=20):
    try:
        code = str(uuid.uuid1()).replace('-', '')
        Coupon(user=user,
               total_amount=total_amount,
               point=point,
               comment=comment,
               code=code).save()
        return True
    except Exception as e:
        logging.error(e)
        return False


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
        ding(f'短信验证码发送失败: {str(e)}')
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
                ding(f'验证码识别成功: {code}')
                return code
            ding(f'验证码识别失败: {r.content.decode()}')
            return None
        ding(f'验证码识别请求失败: {r.status_code} {r.content.decode()}')
        return None


def get_random_ua():
    """
    随机获取User-Agent

    :return:
    """

    ua_list = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',  # Google Chrome
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/82.0.4083.0 Safari/537.36 Edg/82.0.456.0',  # Microsoft Edge
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15',  # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:74.0) Gecko/20100101 Firefox/74.0'  # Firefox
    ]
    return random.choice(ua_list)


def upload_csdn_resource(resource):
    headers = {
        'cookie': CsdnAccount.objects.get(email='hsowan.v@gmail.com').cookies,
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
        desc = resource.desc + ' 该资源是由 weixin_46449765 用户进行上传的，来源于网络，如有侵权，请联系本人进行删除！'
    else:
        desc = resource.desc

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
                     logger=logging.error)

            if resp['code'] == 200:
                # 上传成功
                ding('资源上传到CSDN成功')
            else:
                # 上传失败
                ding('资源上传到CSDN失败',
                     error=resp,
                     logger=logging.error)


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
