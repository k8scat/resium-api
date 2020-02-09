# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import datetime
import json
import logging
import random
import time
import uuid

import alipay
import requests
from bs4 import BeautifulSoup
from django.conf import settings

import os
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

from downloader.models import Resource, DownloadRecord, CsdnAccount, BaiduAccount


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
    try:
        return bucket.object_exists(key)
    except NoSuchKey:
        return None


def aliyun_oss_sign_url(key):
    """
    获取文件临时下载链接，使用签名URL进行临时授权

    参考: https://help.aliyun.com/document_detail/32033.html?spm=a2c4g.11186623.6.881.603f16950kd10U

    :param key:
    :return:
    """

    bucket = get_aliyun_oss_bucket()
    return bucket.sign_url('GET', key, 60 * 60)


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


def check_oss(resource_url):
    """
    检查oss是否已存储资源

    :return: Resource
    """

    try:
        resource = Resource.objects.get(url=resource_url)
        # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
        # 如果oss上没有存储资源，则将resource删除
        if not aliyun_oss_check_file(resource.key):
            resource.delete()
            resource = None
        return resource
    except Resource.DoesNotExist:
        return None


def check_download(save_dir):
    """
    判断文件是否下载完成

    :param save_dir:
    :return:
    """
    while True:
        files = os.listdir(save_dir)
        if len(files) == 0 or files[0].endswith('.crdownload'):
            logging.info('Downloading')
            time.sleep(0.1)
            continue
        else:
            time.sleep(0.1)
            logging.info('Download ok')
            break

    # 下载完成后，文件夹下存在唯一的文件
    filename = files[0]
    # 生成文件的绝对路径
    filepath = os.path.join(save_dir, filename)

    return filepath, filename


def add_cookie(driver, platform):
    """
    给driver添加cookies

    :param driver:
    :param platform: csdn or baidu
    :return: CsdnAccount or BaiduAccount
    """

    if platform == 'csdn':
        account = random.choice(CsdnAccount.objects.all())
        cookies = json.loads(account.cookies)
    elif platform == 'baidu':
        account = random.choice(BaiduAccount.objects.all())
        cookies = json.loads(account.cookies)

    for cookie in cookies:
        if 'expiry' in cookie:
            del cookie['expiry']
        driver.add_cookie(cookie)

    return account


def get_driver(unique_folder):
    """
    获取driver

    :param unique_folder: 唯一文件夹
    :return: WebDriver
    """
    options = webdriver.ChromeOptions()
    prefs = {
        "download.prompt_for_download": False,
        'download.default_directory': '/download/' + unique_folder,  # 下载目录
        "plugins.always_open_pdf_externally": True,
        'profile.default_content_settings.popups': 0,  # 设置为0，禁止弹出窗口
        'profile.default_content_setting_values.images': 2,  # 禁止图片加载
    }
    options.add_experimental_option('prefs', prefs)

    caps = DesiredCapabilities.CHROME
    # 线上使用selenium server
    driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps,
                              options=options)

    # 本地图形界面自动化测试
    # driver = webdriver.Chrome(options=options)
    return driver


def check_csdn():
    """
    检查csdn 当天是否可下载

    上传下载相关问题
    https://blog.csdn.net/blogdevteam/article/details/103487272

    Q：重复下载资源扣下载积分吗？
    A：第一次下载资源扣下载积分，以后此资源下载30日内都为免费，如果发现扣分现象，请及时联系客服。30日后再次下载需要扣除相应的积分。

    :return: bool
    """

    # 这个今日资源下载数计算可能包含了以前下载过的资源，所以存在误差，偏大
    today_download_count = DownloadRecord.objects.filter(create_time__day=datetime.date.today().day,
                                                         is_deleted=False, resource_url__startswith='https://download.csdn.net/download/').values('resource_url').distinct().count()
    if today_download_count == 20:
        return False
    return True


def save_csdn_resource(resource_url, filename, file, title):
    """
    保存CSDN资源记录并上传到oss

    :param resource_url:
    :param filename:
    :param file:
    :param title:
    :return:
    """
    # 判断资源记录是否已存在，如果已存在则直接返回
    if Resource.objects.filter(url=resource_url).count():
        return

    # 存储在oss中的key
    key = str(uuid.uuid1()) + '-' + filename
    upload_success = aliyun_oss_upload(file, key)
    if not upload_success:
        ding('阿里云OSS上传资源失败')
        return

    r = requests.get(resource_url)
    if r.status_code == 200:
        try:
            # 资源文件大小
            size = os.path.getsize(file)
            soup = BeautifulSoup(r.text, 'lxml')
            desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
            category = '-'.join([cat.string for cat in soup.select('div.csdn_dl_bread a')[1:3]])
            tags = settings.TAG_SEP.join(
                [tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')])

            Resource.objects.create(title=title, filename=filename, size=size, desc=desc,
                                    url=resource_url, category=category, key=key, tags=tags)
        except Exception as e:
            logging.error(e)
            ding('资源信息保存失败 ' + str(e))
    else:
        ding('资源信息保存失败 - 资源请求失败')


def save_wenku_resource(resource_url, filename, file, title, tags, category):
    """
    保存百度文库资源记录并上传到oss

    :param resource_url:
    :param filename:
    :param file:
    :param title:
    :param tags:
    :param category:
    :return:
    """

    # 判断资源记录是否已存在，如果已存在则直接返回
    if Resource.objects.filter(url=resource_url).count():
        return

    # 存储在oss中的key
    key = str(uuid.uuid1()) + '-' + filename
    upload_success = aliyun_oss_upload(file, key)
    if not upload_success:
        ding('阿里云OSS上传资源失败')
        return

    try:
        # 资源文件大小
        size = os.path.getsize(file)
        Resource.objects.create(title=title, filename=filename, size=size,
                                url=resource_url, category=category, key=key, tags=tags)
    except Exception as e:
        logging.error(e)
        ding('资源信息保存失败 ' + str(e))


