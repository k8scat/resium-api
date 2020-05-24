# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
from time import sleep

from django.template.loader import render_to_string
from django.utils.html import strip_tags

from downloader.utils import *
from downloader.models import *
import json
import logging
import os
import random
import re
import string
import uuid
from json import JSONDecodeError
from threading import Thread
from urllib import parse
import requests
from PIL import Image
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse, FileResponse
from ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from downloader.decorators import auth
from downloader.serializers import ResourceSerializers, ResourceCommentSerializers


class BaseResource:
    def __init__(self, url, user):
        self.url = url
        self.user = user
        self.unique_folder = None
        self.save_dir = None
        self.filepath = None
        self.filename = None
        self.resource = None
        self.account = None

    def _before_download(self):
        """
        调用download前必须调用_before_download

        :return:
        """

        logging.info(f'资源下载: {self.url}')

        # 生成资源存放的唯一子目录
        self.unique_folder = str(uuid.uuid1())
        self.save_dir = os.path.join(settings.DOWNLOAD_DIR, self.unique_folder)
        while True:
            if os.path.exists(self.save_dir):
                self.unique_folder = str(uuid.uuid1())
                self.save_dir = os.path.join(settings.DOWNLOAD_DIR, self.unique_folder)
            else:
                os.mkdir(self.save_dir)
                break

    def send_email(self, url):
        subject = '[源自下载] 资源下载成功'
        html_message = render_to_string('downloader/download_url.html', {'url': url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[self.user.email],
                      html_message=html_message,
                      fail_silently=False)
            return 200, '下载成功，请前往邮箱查收！'
        except Exception as e:
            ding('资源下载地址邮件发送失败',
                 error=e,
                 uid=self.user.uid,
                 used_account=self.account.email,
                 logger=logging.error)
            return 500, '邮件发送失败'

    def parse(self):
        pass

    def __download(self):
        pass

    def get_filepath(self):
        """
        返回文件路径

        :return:
        """

        pass

    def get_url(self, use_email=False):
        """
        返回下载链接

        :param use_email: 是否使用邮件
        :return:
        """

        pass


class CsdnResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        headers = {
            'authority': 'download.csdn.net',
            'referer': 'https://download.csdn.net/',
            'user-agent': get_random_ua()
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    # 版权受限，无法下载
                    # https://download.csdn.net/download/c_baby123/10791185
                    can_download = len(soup.select('div.resource_box a.copty-btn')) == 0
                    if can_download:
                        point = settings.CSDN_POINT
                    else:
                        point = None
                    self.resource = {
                        'title': soup.find('span', class_='resource_title').string,
                        'desc': soup.select('div.resource_description p')[0].text,
                        'tags': [tag.text for tag in soup.select('label.resource_tags a')],
                        'file_type': soup.select('strong.info_box span')[3].text,
                        'point': point,
                        'size': soup.select('strong.info_box span')[2].text
                    }
                    return 200, self.resource
                except Exception as e:
                    ding('[CSDN] 资源信息解析失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid)
                    return 500, '资源获取失败'
            return

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != 200:
            return status, result

        try:
            self.account = CsdnAccount.objects.get(is_enabled=True)
            point = settings.CSDN_POINT
            # 可用积分不足
            if self.user.point < point:
                return 400, '积分不足，请前往网站捐赠支持'

            # 判断账号当天下载数
            if self.account.today_download_count >= 20:
                ding(f'[CSDN] 今日下载数已用完',
                     uid=self.user.uid,
                     resource_url=self.url,
                     used_account=self.account.email)
                # 自动切换CSDN
                switch_csdn_account(self.account)
                return 403, '下载出了点小问题，请尝试重新下载'
        except CsdnAccount.DoesNotExist:
            ding('[CSDN] 没有可用账号',
                 uid=self.user.uid,
                 resource_url=self.url)
            return 500, '下载失败，请联系管理员'

        if self.resource['point'] is None:
            ding('[CSDN] 用户尝试下载版权受限的资源',
                 uid=self.user.uid,
                 resource_url=self.url)
            return 400, '版权受限，无法下载'

        resource_id = self.url.split('/')[-1]
        headers = {
            'cookie': self.account.cookies,
            'user-agent': get_random_ua(),
            'referer': self.url  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
        }
        with requests.get(f'https://download.csdn.net/source/download?source_id={resource_id}',
                          headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    resp = r.json()
                except JSONDecodeError:
                    ding('[CSDN] 下载失败',
                         error=r.text,
                         resource_url=self.url,
                         uid=self.user.uid,
                         used_account=self.account.email,
                         logger=logging.error)
                    return 500, '下载失败'
                if resp['code'] == 200:
                    # 更新账号今日下载数
                    self.account.today_download_count += 1
                    self.account.used_count += 1
                    self.account.save()

                    # 更新用户的剩余积分和已用积分
                    self.user.point -= point
                    self.user.used_point += point
                    self.user.save()

                    with requests.get(resp['data'], headers=headers, stream=True) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            self.filename = parse.unquote(download_resp.headers['Content-Disposition'].split('"')[1])
                            self.filepath = os.path.join(self.save_dir, self.filename)
                            # 写入文件，用于线程上传资源到OSS
                            with open(self.filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                            return 200, '下载成功'

                        ding('[CSDN] 下载失败',
                             error=download_resp.text,
                             uid=self.user.uid,
                             resource_url=self.url,
                             used_account=self.account.email,
                             logger=logging.error)
                        return 500, '下载失败'
                else:
                    if resp.get('message', None) == '当前资源不开放下载功能':
                        return 400, 'CSDN未开放该资源的下载功能'
                    elif resp.get('message', None) == '短信验证':
                        ding('[CSDN] 下载失败，需要短信验证',
                             error=resp,
                             uid=self.user.uid,
                             resource_url=self.url,
                             used_account=self.account.email,
                             logger=logging.error)
                        # 自动切换CSDN
                        switch_csdn_account(self.account, need_sms_validate=True)
                        return 500, '下载出了点小问题，请尝试重新下载'

                    ding('[CSDN] 下载失败',
                         error=resp,
                         uid=self.user.uid,
                         resource_url=self.url,
                         used_account=self.account.email,
                         logger=logging.error)
                    return 500, '下载失败'
            else:
                ding('[CSDN] 下载失败',
                     error=r.text,
                     uid=self.user.uid,
                     resource_url=self.url,
                     used_account=self.account.email,
                     logger=logging.error)
                return 500, '下载失败'

    def get_filepath(self):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 上传资源到OSS并保存记录到数据库
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user),
                   kwargs={'account': self.account.email})
        t.start()
        return 200, dict(filepath=self.filepath, filename=self.filename)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 上传资源到OSS并保存记录到数据库
        download_url = save_resource(resource_url=self.url, filename=self.filename,
                                     filepath=self.filepath, resource_info=self.resource,
                                     user=self.user, account=self.account.email)

        if use_email:
            return self.send_email(download_url)

        if download_url:
            return 200, download_url
        else:
            return 500, '下载出了点小问题，请尝试重新下载'


class WenkuResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        """
        资源信息获取地址: https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id=
        """
        # https://wenku.baidu.com/view/c3853acaab00b52acfc789eb172ded630b1c9809.htm
        doc_id = self.url.split('?')[0].split('://wenku.baidu.com/view/')[1].split('.')[0]
        logging.info(f'百度文库文档ID: {doc_id}')

        get_doc_info_url = f'https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id={doc_id}'
        get_vip_free_doc_url = f'https://wenku.baidu.com/user/interface/getvipfreedoc?doc_id={doc_id}'
        headers = {
            'user-agent': get_random_ua()
        }
        with requests.get(get_doc_info_url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    data = json.loads(r.content.decode()[7:-1])
                    doc_info = data['docInfo']
                    # 判断是否是VIP专享文档
                    if doc_info.get('professionalDoc', None) == 1:
                        point = settings.WENKU_SPECIAL_DOC_POINT
                        wenku_type = 'VIP专项文档'
                    elif doc_info.get('isPaymentDoc', None) == 0:
                        with requests.get(get_vip_free_doc_url, headers=headers) as _:
                            if _.status_code == requests.codes.OK and _.json()['status']['code'] == 0:
                                if _.json()['data']['is_vip_free_doc']:
                                    point = settings.WENKU_VIP_FREE_DOC_POINT
                                    wenku_type = 'VIP免费文档'
                                else:
                                    point = settings.WENKU_SHARE_DOC_POINT
                                    wenku_type = '共享文档'
                            else:
                                return 500, '资源获取失败'
                    else:
                        point = None

                    file_type = doc_info['docType']
                    if file_type == '6':
                        file_type = 'PPTX'
                    elif file_type == '3':
                        file_type = 'PPT'
                    elif file_type == '1':
                        file_type = 'DOC'
                    elif file_type == '4':
                        file_type = 'DOCX'
                    elif file_type == '8':
                        file_type = 'TXT'
                    elif file_type == '7':
                        file_type = 'PDF'
                    elif file_type == '5':
                        file_type = 'XLSX'
                    elif file_type == '2':
                        file_type = 'XLS'
                    elif file_type == '12':
                        file_type = 'VSD'
                    elif file_type == '15':
                        file_type = 'PPS'
                    elif file_type == '13':
                        file_type = 'RTF'
                    elif file_type == '9':
                        file_type = 'WPS'
                    elif file_type == '19':
                        file_type = 'DWG'
                    else:
                        ding(f'未知文件格式: {file_type}',
                             resource_url=self.url,
                             error=doc_info)
                        file_type = 'UNKNOWN'

                    self.resource = {
                        'title': doc_info['docTitle'],
                        'tags': doc_info.get('newTagArray', []),
                        'desc': doc_info['docDesc'],
                        'file_type': file_type,
                        'point': point,
                        'wenku_type': wenku_type
                    }
                    return 200, self.resource
                except Exception as e:
                    ding(f'资源信息解析失败: {str(e)}',
                         resource_url=self.url,
                         uid=self.user.uid,
                         logger=logging.error)
                    return 500, '资源获取失败'
            else:
                return 500, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != 200:
            return status, result

        point = self.resource['point']
        if point is None:
            return 400, '该资源不支持下载'

        if self.user.point < point:
            return 400, '积分不足，请前往网站捐赠支持'

        # 更新用户积分
        self.user.point -= point
        self.user.used_point += point
        self.user.save()

        driver = get_driver(self.unique_folder)
        try:
            if self.resource['wenku_type'] == '共享文档':
                self.account = random.choice(TaobaoWenkuAccount.objects.filter(is_enabled=True).all())
                driver.get('http://doc110.com/#/login/')
                account_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "(//input[@type='text'])[2]")
                    )
                )
                account_input.send_keys(self.account.account)
                password_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "(//input[@type='password'])[2]")
                    )
                )
                password_input.send_keys(self.account.password)
                login_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "(//a[contains(text(),'立即登陆')])[2]")
                    )
                )
                login_button.click()

                url_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@class='is-accept']/input[@class='input']")
                    )
                )
                url_input.send_keys(self.url)

                download_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@class='is-accept']/a[@class='btn-lg'][1]")
                    )
                )
                download_button.click()
            else:
                try:
                    self.account = BaiduAccount.objects.get(is_enabled=True)
                except BaiduAccount.DoesNotExist:
                    ding('没有可用的百度文库账号',
                         uid=self.user.uid,
                         resource_url=self.url)
                    return 500, '下载失败'

                driver.get('https://www.baidu.com/')
                # 添加cookies
                cookies = json.loads(self.account.cookies)
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    driver.add_cookie(cookie)
                driver.get(self.url)
                if self.resource['wenku_type'] == 'VIP免费文档':
                    self.account.vip_free_count += 1
                elif self.resource['wenku_type'] == 'VIP专项文档':
                    self.account.special_doc_count += 1
                self.account.save()

                # 显示下载对话框的按钮
                show_download_modal_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.reader-download.btn-download'))
                )
                show_download_modal_button.click()
                # 下载按钮
                try:
                    # 首次下载
                    download_button = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'div.dialog-inner.tac > a.ui-bz-btn-senior.btn-diaolog-downdoc'))
                    )
                    # 取消转存网盘
                    cancel_wp_upload_check = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.wpUpload input'))
                    )
                    cancel_wp_upload_check.click()
                    download_button.click()
                except TimeoutException:
                    if self.resource['wenku_type'] != 'VIP专享文档':
                        # 已转存过此文档
                        download_button = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'WkDialogOk'))
                        )
                        download_button.click()
                    else:
                        ding('百度文库下载失败',
                             uid=self.user.uid,
                             used_account=self.account.email,
                             resource_url=self.url,
                             logger=logging.error)
                        return 500, '下载失败'

            status, result = check_download(self.save_dir)
            if status == 200:
                self.filename = result['filename']
                self.filepath = result['filepath']
                return 200, '下载成功'
            else:
                return status, result
        except Exception as e:
            ding('[百度文库] 下载失败',
                 error=e,
                 uid=self.user.uid,
                 used_account=self.account.email if isinstance(self.account, BaiduAccount) else self.account.account,
                 resource_url=self.url)
            return 500, '下载失败'
        finally:
            driver.close()

    def get_filepath(self):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user),
                   kwargs={'account': self.account.email if isinstance(self.account,
                                                                       BaiduAccount) else self.account.account})
        t.start()
        return 200, dict(filepath=self.filepath, filename=self.filename)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != 200:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filepath=self.filepath, filename=self.filename,
                                     user=self.user,
                                     account=self.account.email if isinstance(self.account,
                                                                              BaiduAccount) else self.account.account)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return 200, download_url
        else:
            return 500, '下载出了点小问题，请尝试重新下载'


class DocerResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        headers = {
            'referer': 'https://www.docer.com/',
            'user-agent': get_random_ua()
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.text, 'lxml')
                tags = [tag.text for tag in soup.select('li.preview__labels-item.g-link a')]
                if '展开更多' in tags:
                    tags = tags[:-1]

                # 获取所有的预览图片
                preview_images = DocerPreviewImage.objects.filter(resource_url=self.url).all()
                if len(preview_images) > 0:
                    preview_images = [
                        {
                            'url': preview_image.url,
                            'alt': preview_image.alt,

                        } for preview_image in preview_images
                    ]
                else:
                    driver = get_driver()
                    try:
                        driver.get(self.url)
                        all_images = WebDriverWait(driver, 5).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, '//ul[@class="preview__img-list"]//img')
                            )
                        )
                        preview_images = []
                        preview_image_models = []
                        for image in all_images:
                            image_url = image.get_attribute('data-src')
                            image_alt = image.get_attribute('alt')
                            preview_images.append({
                                'url': image_url,
                                'alt': image_alt
                            })
                            preview_image_models.append(DocerPreviewImage(resource_url=self.url,
                                                                          url=image_url,
                                                                          alt=image_alt))
                        DocerPreviewImage.objects.bulk_create(preview_image_models)
                    finally:
                        driver.close()

                self.resource = {
                    'title': soup.find('div', class_='preview-info_title').string,
                    'tags': tags,
                    'file_type': soup.select('span.m-crumbs-path a')[0].text,
                    'desc': '',  # soup.find('meta', attrs={'name': 'Description'})['content']
                    'point': settings.DOCER_POINT,
                    'is_docer_vip_doc': r.text.count('类型：VIP模板') > 0,
                    'preview_images': preview_images
                }
                return 200, self.resource

            return 500, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != 200:
            return status, result

        point = settings.DOCER_POINT
        if self.user.point < point:
            return 400, '积分不足，请前往网站捐赠支持'

        try:
            self.account = DocerAccount.objects.get(is_enabled=True)
        except DocerAccount.DoesNotExist:
            ding('没有可以使用的稻壳VIP模板账号',
                 uid=self.user.uid,
                 resource_url=self.url,
                 logger=logging.error)
            return 500, '下载失败'

        # 下载资源
        resource_id = self.url.split('/')[-1]
        parse_url = f'https://www.docer.com/detail/dl?id={resource_id}'
        headers = {
            'cookie': self.account.cookies,
            'user-agent': get_random_ua()
        }
        # 如果cookies失效，r.json()会抛出异常
        with requests.get(parse_url, headers=headers) as r:
            try:
                resp = r.json()
                if resp['result'] == 'ok':
                    # 更新用户积分
                    self.user.point -= point
                    self.user.used_point += point
                    self.user.save()

                    # 更新账号使用下载数
                    self.account.used_count += 1
                    self.account.save()

                    download_url = resp['data']
                    self.filename = download_url.split('/')[-1]
                    self.filepath = os.path.join(self.save_dir, self.filename)
                    with requests.get(download_url, stream=True) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            with open(self.filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)

                            return 200, '下载成功'

                        ding('[稻壳VIP模板] 下载失败',
                             error=download_resp.text,
                             uid=self.user.uid,
                             used_account=self.account.email,
                             resource_url=self.url,
                             logger=logging.error)
                        return 500, '下载失败'
                else:
                    ding('[稻壳VIP模板] 下载失败',
                         error=r.text,
                         uid=self.user.uid,
                         resource_url=self.url,
                         logger=logging.error)
                    return 500, '下载失败'
            except JSONDecodeError:
                ding('[稻壳VIP模板] Cookies失效',
                     uid=self.user.uid,
                     resource_url=self.url,
                     logger=logging.error)
                return 500, '下载失败'

    def get_filepath(self):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user),
                   kwargs={'account': self.account.email})
        t.start()
        return 200, dict(filepath=self.filepath, filename=self.filename)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != 200:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filename=self.filename, filepath=self.filepath,
                                     user=self.user, account=self.account.email)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return 200, download_url
        else:
            return 500, '下载出了点小问题，请尝试重新下载'


class ZhiwangResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        """
        需要注意的是知网官方网站和使用了VPN访问的网站是不一样的

        :return:
        """

        headers = {
            'referer': self.url,
            'user-agent': get_random_ua()
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    # 获取标签
                    tags = []
                    for tag in soup.select('p.keywords a'):
                        tags.append(tag.string.strip()[:-1])

                    title = soup.select('div.wxTitle h2')[0].text
                    desc = soup.find('span', attrs={'id': 'ChDivSummary'}).string
                    has_pdf = True if soup.find('a', attrs={'id': 'pdfDown'}) else False
                    self.resource = {
                        'title': title,
                        'desc': desc,
                        'tags': tags,
                        'pdf_download': has_pdf,  # 是否支持pdf下载
                        'point': settings.ZHIWANG_POINT
                    }
                    return 200, self.resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         resource_url=self.url)
                    return 500, '资源获取失败'
            else:
                return 500, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != 200:
            return status, result

        point = settings.ZHIWANG_POINT
        if self.user.point < point:
            return 400, '积分不足，请前往网站捐赠支持'

        # url = resource_url.replace('https://kns.cnki.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn')
        vpn_url = re.sub(r'http(s)?://kns(8)?\.cnki\.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn', self.url)

        driver = get_driver(self.unique_folder, load_images=True)
        try:
            driver.get('http://wvpn.ncu.edu.cn/users/sign_in')
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'user_login'))
            )
            username_input.send_keys(settings.NCU_VPN_USERNAME)
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'user_password'))
            )
            password_input.send_keys(settings.NCU_VPN_PASSWORD)
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='col-md-6 col-md-offset-6 login-btn']/input")
                )
            )
            submit_button.click()

            driver.get(vpn_url)
            driver.refresh()

            try:
                # pdf下载
                download_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, 'pdfDown')
                    )
                )
            except TimeoutException:
                return 400, '该文献不支持下载PDF'

            self.user.point -= point
            self.user.used_point += point
            self.user.save()

            # 获取下载链接
            download_link = download_button.get_attribute('href')
            # 访问下载链接
            driver.get(download_link)
            try:
                # 获取验证码图片
                code_image = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located(
                        (By.ID, 'vImg')
                    )
                )
                # 自动获取截取位置
                # left = int(code_image.location['x'])
                # print(left)
                # upper = int(code_image.location['y'])
                # print(upper)
                # right = int(code_image.location['x'] + code_image.size['width'])
                # print(right)
                # lower = int(code_image.location['y'] + code_image.size['height'])
                # print(lower)

                # 获取截图
                driver.get_screenshot_as_file(settings.SCREENSHOT_IMAGE)

                # 手动设置截取位置
                left = 430
                upper = 275
                right = 620
                lower = 340
                # 通过Image处理图像
                img = Image.open(settings.SCREENSHOT_IMAGE)
                # 剪切图片
                img = img.crop((left, upper, right, lower))
                # 保存剪切好的图片
                img.save(settings.CODE_IMAGE)

                code = predict_code(settings.CODE_IMAGE)
                if code:
                    code_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, 'vcode')
                        )
                    )
                    code_input.send_keys(code)
                    submit_code_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//dl[@class='c_verify-code']/dd/button")
                        )
                    )
                    submit_code_button.click()
                else:
                    return 500, '下载失败'

            finally:
                status, result = check_download(self.save_dir)
                if status == 200:
                    self.filename = result['filename']
                    self.filepath = result['filepath']
                    return 200, '下载成功'
                else:
                    return status, result

        except Exception as e:
            ding('[知网文献] 下载失败',
                 error=e,
                 uid=self.user.uid,
                 resource_url=self.url,
                 logger=logging.error)
            return 500, '下载失败'

        finally:
            driver.close()

    def get_filepath(self):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user))
        t.start()
        return 200, dict(filepath=self.filepath, filename=self.filename)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != 200:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filepath=self.filepath, filename=self.filename,
                                     user=self.user)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return 200, download_url
        else:
            return 500, '下载出了点小问题，请尝试重新下载'


class QiantuResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        with requests.get(self.url) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    title = soup.select('span.pic-title.fl')[0].string
                    info = soup.select('div.material-info p')
                    size = info[2].string.replace('文件大小：', '')
                    # Tag有find方法，但没有select方法
                    file_type = info[4].find('span').contents[0]
                    tags = [tag.string for tag in soup.select('div.mainRight-tagBox a')]
                    self.resource = {
                        'title': title,
                        'size': size,
                        'tags': tags,
                        'desc': '',
                        'file_type': file_type,
                        'point': settings.QIANTU_POINT
                    }
                    return 200, self.resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         resource_url=self.url)
                    return 500, "资源获取失败"

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != 200:
            return status, result

        try:
            self.account = QiantuAccount.objects.get(is_enabled=True)
        except QiantuAccount.DoesNotExist:
            return 500, "[千图网] 没有可用账号"

        headers = {
            'cookie': self.account.cookies,
            'referer': self.url,
            'user-agent': get_random_ua()
        }
        download_url = self.url.replace('https://www.58pic.com/newpic/', 'https://dl.58pic.com/')
        with requests.get(download_url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    download_url = soup.select('a.clickRecord.autodown')[0]['href']
                    self.filename = download_url.split('?')[0].split('/')[-1]
                    self.filepath = os.path.join(self.save_dir, self.filename)
                    with requests.get(download_url, stream=True, headers=headers) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            with open(self.filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)

                            return 200, '下载成功'

                        ding('[千图网] 下载失败',
                             error=download_resp.text,
                             uid=self.user.uid,
                             used_account=self.account.email,
                             resource_url=self.url,
                             logger=logging.error)
                        return 500, '下载失败'
                except Exception as e:
                    ding('[千图网] 下载失败',
                         error=e,
                         uid=self.user.uid,
                         resource_url=self.url,
                         logger=logging.error,
                         used_account=self.account.email)
                    return 500, "下载失败"

    def get_filepath(self):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user),
                   kwargs={'account': self.account.email})
        t.start()
        return 200, dict(filepath=self.filepath, filename=self.filename)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != 200:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filename=self.filename, filepath=self.filepath,
                                     user=self.user, account=self.account.email)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return 200, download_url
        else:
            return 500, '下载出了点小问题，请尝试重新下载'


class PudnResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        with requests.get(self.url) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    title = soup.select('div.item-name')[0].string
                    desc = soup.select('div.item-intro')[0].contents
                    desc = desc[0].strip()[5:] + '\n' + desc[2].strip()
                    size = soup.select('div.item-info')[0].contents[11][1:]
                    tags = [tag.string for tag in soup.select('div.item-keyword a')]
                    self.resource = {
                        'title': title,
                        'size': size,
                        'tags': tags,
                        'desc': desc,
                        'point': settings.PUDN_POINT
                    }
                    return 200, self.resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         resource_url=self.url)
                    return 500, "资源获取失败"

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != 200:
            return status, result

        try:
            self.account = PudnAccount.objects.get(is_enabled=True)
        except PudnAccount.DoesNotExist:
            return 500, "[PUDN] 没有可用账号"

        point = settings.DOCER_POINT
        if self.user.point < point:
            return 400, '积分不足，请前往网站捐赠支持'

        driver = get_driver(self.unique_folder)
        try:
            driver.get('http://www.pudn.com/User/login.html')
            email_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='login-form']/div[@class='form-group'][1]/input")
                )
            )
            email_input.send_keys(self.account.email)
            password_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='login-form']/div[@class='form-group'][2]/input")
                )
            )
            password_input.send_keys(self.account.password)
            code_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='login-form']/div[@class='form-group'][3]/input")
                )
            )
            code_input.send_keys('abcd')
            login_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[@id='login-form']/button")
                )
            )
            login_button.click()
            try:
                logout = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@id='navbar']/ul[@class='navbar-user navbar-right']/li[6]/a")
                    )
                )
                if logout.text == '退出':
                    # 更新用户积分
                    self.user.point -= point
                    self.user.used_point += point
                    self.user.save()

                    driver.get(self.url)
                    resource_id = self.url.split('id/')[1].split('.')[0]
                    driver.get(f'http://www.pudn.com/Download/dl/id/{resource_id}')
                    download_button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[1]")
                        )
                    )
                    download_button.click()

                    status, result = check_download(self.save_dir)
                    if status == 200:
                        self.filename = result['filename']
                        self.filepath = result['filepath']
                        return 200, '下载成功'
                    else:
                        return status, result
                else:
                    ding('[PUDN] 登录失败，退出按钮文字判断出错',
                         uid=self.user.uid,
                         used_account=self.account.email,
                         resource_url=self.url)
                    return 500, '下载失败'
            except TimeoutException as e:
                ding('[PUDN] 登录失败，退出按钮获取失败',
                     error=e,
                     uid=self.user.uid,
                     used_account=self.account.email,
                     resource_url=self.url)
                return 500, '下载失败'

        except Exception as e:
            ding('[PUDN] 下载失败',
                 error=e,
                 uid=self.user.uid,
                 used_account=self.account.email,
                 resource_url=self.url)
            return 500, '下载失败'
        finally:
            driver.close()

    def get_filepath(self):
        status, result = self.__download()
        if status != 200:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user),
                   kwargs={'account': self.account.email})
        t.start()
        return 200, dict(filepath=self.filepath, filename=self.filename)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != 200:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filepath=self.filepath, filename=self.filename,
                                     user=self.user,
                                     account=self.account.email)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return 200, download_url
        else:
            return 500, '下载出了点小问题，请尝试重新下载'


@auth
@api_view(['POST'])
def upload(request):
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未登录'))

    file = request.FILES.get('file', None)
    if not file:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    if file.size > (2 * 10) * 1024 * 1024:
        return JsonResponse(dict(code=400, msg='上传资源大小不能超过20MiB'))

    file_md5 = get_file_md5(file.open('rb'))
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=400, msg='资源已存在'))

    data = request.POST
    title = data.get('title', None)
    tags = data.get('tags', None)
    desc = data.get('desc', None)
    if title and tags and desc and file:
        try:
            filename = file.name
            key = f'{str(uuid.uuid1())}-{filename}'
            logging.info(f'Upload resource: {key}')
            filepath = os.path.join(settings.UPLOAD_DIR, key)
            # 写入文件，之后使用线程进行上传
            with open(filepath, 'wb') as f:
                for chunk in file.chunks():
                    f.write(chunk)
            Resource(title=title, desc=desc, tags=tags,
                     filename=filename, size=file.size,
                     download_count=0, is_audited=0, key=key,
                     user=user, file_md5=file_md5, local_path=filepath).save()

            # 开线程上传资源到OSS
            t = Thread(target=aliyun_oss_upload, args=(filepath, key))
            t.start()

            ding(f'有新的资源上传 {key}',
                 uid=user.uid)
            return JsonResponse(dict(code=200, msg='资源上传成功'))
        except Exception as e:
            logging.error(e)
            ding(f'资源上传失败: {str(e)}')
            return JsonResponse(dict(code=500, msg='资源上传失败'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view()
def check_file(request):
    """
    根据md5值判断资源是否存在

    :param request:
    :return:
    """

    file_md5 = request.GET.get('hash', None)
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=400, msg='资源已存在'))
    return JsonResponse(dict(code=200, msg='资源不存在'))


@auth
@api_view()
def list_uploaded_resources(request):
    """
    获取用户上传资源

    :param request:
    :return:
    """

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
        resources = Resource.objects.order_by('-create_time').filter(user=user).all()
        return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view()
def get_resource(request):
    resource_id = request.GET.get('id', None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
        try:
            resource = Resource.objects.get(id=resource_id, is_audited=1)
            preview_images = []
            if resource.url and re.match(settings.PATTERN_DOCER, resource.url):
                preview_images = [
                    {
                        'url': preview_image.url,
                        'alt': preview_image.alt
                    } for preview_image in DocerPreviewImage.objects.filter(resource_url=resource.url).all()
                ]
            resource_ = ResourceSerializers(resource).data
            # todo: 可以尝试通过django-rest-framework实现，而不是手动去获取预览图的数据
            resource_.setdefault('preview_images', preview_images)
            resource_.setdefault('point', settings.OSS_RESOURCE_POINT + resource.download_count - 1)
            return JsonResponse(dict(code=200, resource=resource_))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=404, msg='资源不存在'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view()
def list_comments(request):
    resource_id = request.GET.get('id', None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
        try:
            comments = ResourceComment.objects.filter(resource_id=resource_id).all()
            return JsonResponse(dict(code=200, comments=ResourceCommentSerializers(comments, many=True).data))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=404, msg='资源不存在'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@ratelimit(key='ip', rate='1/5m', block=True)
@api_view(['POST'])
def create_comment(request):
    content = request.data.get('content', None)
    resource_id = request.data.get('id', None)
    user_id = request.data.get('user_id', None)
    if content and resource_id and user_id and resource_id.isnumeric() and user_id.isnumeric():
        resource_id = int(resource_id)
        user_id = int(user_id)
        try:
            resource = Resource.objects.get(id=resource_id, is_audited=1)
            user = User.objects.get(id=user_id)
            ResourceComment(user=user, resource=resource, content=content).save()
            return JsonResponse(dict(code=200, msg='评论成功'))
        except (User.DoesNotExist, Resource.DoesNotExist):
            return JsonResponse(dict(code=400, msg='错误的请求'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view()
def list_resources(request):
    """
    分页获取资源
    """
    page = request.GET.get('page', None)
    if page is None:
        page = 1
    elif page and page.isnumeric():
        page = int(page)
        if page < 1:
            page = 1
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    count = request.GET.get('count', None)
    if count is None:
        count = 5
    elif count and count.isnumeric():
        count = int(count)
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    key = request.GET.get('key', '')

    start = count * (page - 1)
    end = start + count
    # https://cloud.tencent.com/developer/ask/81558
    resources = Resource.objects.order_by('-create_time').filter(Q(is_audited=1),
                                                                 Q(title__icontains=key) |
                                                                 Q(desc__icontains=key) |
                                                                 Q(tags__icontains=key)).all()[start:end]
    return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))


@api_view()
def get_resource_count(request):
    """
    获取资源的数量
    """
    key = request.GET.get('key', '')
    return JsonResponse(dict(code=200, count=Resource.objects.filter(Q(is_audited=1),
                                                                     Q(title__icontains=key) |
                                                                     Q(desc__icontains=key) |
                                                                     Q(tags__icontains=key)).count()))


@api_view()
def list_resource_tags(request):
    """
    获取所有的资源标签
    """
    tags = Resource.objects.values_list('tags')
    ret_tags = []
    for tag in tags:
        for t in tag[0].split(settings.TAG_SEP):
            if t not in ret_tags and t != '':
                ret_tags.append(t)

    return JsonResponse(dict(code=200, tags=settings.TAG_SEP.join(random.sample(ret_tags, settings.SAMPLE_TAG_COUNT))))


@auth
@api_view(['POST'])
def download(request):
    """
    资源下载
    """

    uid = request.session.get('uid')
    if cache.get(uid) and not settings.DEBUG:
        return JsonResponse(dict(code=403, msg='下载频率过快，请稍后再尝试下载'), status=403)

    try:
        user = User.objects.get(uid=uid)
        if not user.is_admin and not user.can_download:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        if not user.is_admin:
            cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未登录'))

    resource_url = request.data.get('url', None)
    # 下载返回类型（不包括直接在OSS找到的资源），file/url/email，默认file
    t = request.data.get('t', 'file')
    if t == 'email' and not user.email:
        return JsonResponse(dict(code=400, msg='账号未设置邮箱'))

    if not resource_url:
        return JsonResponse(dict(code=400, msg='资源地址不能为空'))

    ding('正在下载',
         resource_url=resource_url,
         uid=uid)

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    # 检查OSS是否存有该资源
    oss_resource = check_oss(resource_url)
    if oss_resource:
        if user.is_admin:
            point = 0
        else:
            point = request.data.get('point', None)
            if point is None or \
                    (re.match(settings.PATTERN_CSDN, resource_url) and point != settings.CSDN_POINT) or \
                    (re.match(settings.PATTERN_WENKU, resource_url) and point not in [settings.WENKU_SHARE_DOC_POINT,
                                                                                      settings.WENKU_SPECIAL_DOC_POINT,
                                                                                      settings.WENKU_VIP_FREE_DOC_POINT]) or \
                    (re.match(settings.PATTERN_DOCER, resource_url) and point != settings.DOCER_POINT) or \
                    (re.match(settings.PATTERN_ZHIWANG, resource_url) and point != settings.ZHIWANG_POINT) or \
                    (re.match(settings.PATTERN_QIANTU, resource_url) and point != settings.QIANTU_POINT) or \
                    (re.match(settings.PATTERN_PUDN, resource_url) and point != settings.PUDN_POINT):
                cache.delete(user.uid)
                return JsonResponse(dict(code=400, msg='错误的请求'))

            if user.point < point:
                cache.delete(user.uid)
                return JsonResponse(dict(code=400, msg='积分不足，请前往网站捐赠支持'))

        # 新增下载记录
        DownloadRecord(user=user,
                       resource=oss_resource,
                       used_point=point).save()

        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()

        # 生成临时下载地址，10分钟有效
        url = aliyun_oss_sign_url(oss_resource.key)

        # 更新资源的下载次数
        oss_resource.download_count += 1
        oss_resource.save()

        if t == 'email':
            subject = '[源自下载] 资源下载成功'
            html_message = render_to_string('downloader/download_url.html', {'url': url})
            plain_message = strip_tags(html_message)
            try:
                send_mail(subject=subject,
                          message=plain_message,
                          from_email=settings.DEFAULT_FROM_EMAIL,
                          recipient_list=[user.email],
                          html_message=html_message,
                          fail_silently=False)
                return JsonResponse(dict(code=200, msg='下载成功，请前往邮箱查收！'))
            except Exception as e:
                ding('资源下载地址邮件发送失败',
                     error=e,
                     uid=user.uid,
                     logger=logging.error)
                return JsonResponse(dict(code=500, msg='邮件发送失败'))

        return JsonResponse(dict(code=200, url=url))

    # CSDN资源下载
    if re.match(settings.PATTERN_CSDN, resource_url):
        resource = CsdnResource(resource_url, user)

    # 百度文库文档下载
    elif re.match(settings.PATTERN_WENKU, resource_url):
        resource = WenkuResource(resource_url, user)

    # 稻壳模板下载
    elif re.match(settings.PATTERN_DOCER, resource_url):
        resource = DocerResource(resource_url, user)

    elif re.match(settings.PATTERN_QIANTU, resource_url):
        resource = QiantuResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        resource = ZhiwangResource(resource_url, user)

    elif re.match(settings.PATTERN_PUDN, resource_url):
        resource = PudnResource(resource_url, user)

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    if t == 'file':
        status, result = resource.get_filepath()
        if status != 200:  # 下载失败
            cache.delete(user.uid)
            return JsonResponse(dict(code=status, msg=result))

        response = FileResponse(open(result['filepath'], 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="' + parse.quote(result['filename'],
                                                                                safe=string.printable) + '"'
        return response

    elif t == 'url':
        status, result = resource.get_url()
        if status != 200:  # 下载失败
            cache.delete(user.uid)
            return JsonResponse(dict(code=status, msg=result))

        return JsonResponse(dict(code=status, url=result))

    elif t == 'email':
        status, result = resource.get_url(use_email=True)
        if status != 200:  # 下载失败
            cache.delete(user.uid)
            return JsonResponse(dict(code=status, msg=result))

        return JsonResponse(dict(code=status, msg=result))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view()
def oss_download(request):
    """
    从OSS上下载资源
    """

    uid = request.session.get('uid')
    if cache.get(uid):
        return JsonResponse(dict(code=403, msg='下载请求过快'), status=403)

    try:
        user = User.objects.get(uid=uid)

        cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未登录'))

    t = request.GET.get('t', 'url')
    if t == 'email' and not user.email:
        return JsonResponse(dict(code=400, msg='账号未设置邮箱'))

    point = settings.OSS_RESOURCE_POINT
    if user.point < point:
        cache.delete(user.uid)
        return JsonResponse(dict(code=400, msg='积分不足，请前往网站捐赠支持'))

    resource_id = request.GET.get('id', None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
    else:
        cache.delete(user.uid)
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        oss_resource = Resource.objects.get(id=resource_id)
        if not aliyun_oss_check_file(oss_resource.key):
            logging.error(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
            ding(f'OSS资源不存在，请及时检查资源 {oss_resource.key}',
                 uid=user.uid,
                 logger=logging.error)
            oss_resource.is_audited = 0
            oss_resource.save()
            cache.delete(user.uid)
            return JsonResponse(dict(code=400, msg='该资源暂时无法下载'))
    except Resource.DoesNotExist:
        cache.delete(user.uid)
        return JsonResponse(dict(code=400, msg='资源不存在'))

    DownloadRecord.objects.create(user=user,
                                  resource=oss_resource,
                                  used_point=settings.OSS_RESOURCE_POINT)

    url = aliyun_oss_sign_url(oss_resource.key)
    oss_resource.download_count += 1
    oss_resource.save()

    if t == 'url':
        return JsonResponse(dict(code=200, url=url))
    elif t == 'email':
        subject = '[源自下载] 资源下载成功'
        html_message = render_to_string('downloader/download_url.html', {'url': url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[user.email],
                      html_message=html_message,
                      fail_silently=False)
            return JsonResponse(dict(code=200, msg='下载成功，请前往邮箱查收！'))
        except Exception as e:
            ding('资源下载地址邮件发送失败',
                 error=e,
                 uid=user.uid,
                 logger=logging.error)
            return JsonResponse(dict(code=500, msg='邮件发送失败'))


@auth
@api_view(['POST'])
def parse_resource(request):
    """
    爬取资源信息

    返回资源信息以及相关资源信息

    :param request:
    :return:
    """

    resource_url = request.data.get('url', None)
    if not resource_url:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    logging.info(resource_url)

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=403, msg='未登录'))

    # CSDN资源
    if re.match(settings.PATTERN_CSDN, resource_url):
        resource = CsdnResource(resource_url, user)

    # 百度文库文档
    elif re.match(settings.PATTERN_WENKU, resource_url):
        resource = WenkuResource(resource_url, user)

    # 稻壳模板
    elif re.match(settings.PATTERN_DOCER, resource_url):
        resource = DocerResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        resource = ZhiwangResource(resource_url, user)

    elif re.match(settings.PATTERN_QIANTU, resource_url):
        resource = QiantuResource(resource_url, user)

    elif re.match(settings.PATTERN_PUDN, resource_url):
        resource = PudnResource(resource_url, user)

    else:
        return JsonResponse(dict(code=400, msg='资源地址有误'))

    status, result = resource.parse()
    return JsonResponse(dict(code=status, resource=result))


@auth
@api_view(['POST'])
def check_resource_existed(request):
    url = request.data.get('url', None)
    if not url:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    is_resource_existed = Resource.objects.filter(url=url).count() > 0
    return JsonResponse(dict(code=200, is_existed=is_resource_existed))


@auth
@api_view(['POST'])
def doc_convert(request):
    command = request.POST.get('c', None)
    file = request.FILES.get('file', None)
    if not command or not file:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    if command == 'pdf2word':
        url = 'https://converter.baidu.com/detail?type=1'
    elif command == 'word2pdf':
        url = 'https://converter.baidu.com/detail?type=12'
    elif command == 'img2pdf':
        url = 'https://converter.baidu.com/detail?type=16'
    elif command == 'pdf2html':
        url = 'https://converter.baidu.com/detail?type=3'
    elif command == 'pdf2ppt':
        url = 'https://converter.baidu.com/detail?type=8'
    elif command == 'pdf2img':
        url = 'https://converter.baidu.com/detail?type=11'
    elif command == 'ppt2pdf':
        url = 'https://converter.baidu.com/detail?type=14'
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
        point = settings.DOC_CONVERT_POINT
        if user.point < point:
            return JsonResponse(dict(code=400, msg='积分不足，请前往网站捐赠支持'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未登录'))

    if file.size > 100 * 1000 * 1000:
        return JsonResponse(dict(code=400, msg='上传资源大小不能超过100MB'))

    unique_folder = str(uuid.uuid1())
    save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
    while True:
        if os.path.exists(save_dir):
            unique_folder = str(uuid.uuid1())
            save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
        else:
            os.mkdir(save_dir)
            break
    filepath = os.path.join(save_dir, file.name)
    with open(filepath, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)

    driver = get_driver(unique_folder)
    try:
        driver.get('https://converter.baidu.com/')
        baidu_account = BaiduAccount.objects.get(is_enabled=True)
        cookies = json.loads(baidu_account.cookies)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
        driver.get(url)
        sleep(3)
        upload_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, 'upload_file'))
        )
        upload_input.send_keys(filepath)
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//p[@class='converterNameV']"))
            )
            download_url = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[@class='dwon-document']"))
            ).get_attribute('href')
            # 保存文档转换记录
            DocConvertRecord(user=user, download_url=download_url,
                             point=point).save()
            # 更新用户积分
            user.point -= point
            user.used_point += point
            user.save()
            ding(f'[文档转换] 转换成功，{download_url}',
                 uid=user.uid)
            return JsonResponse(dict(code=200, url=get_short_url(download_url)))
        except TimeoutException:
            DocConvertRecord(user=user).save()
            ding(f'[文档转换] 转换失败，{command}，{filepath}')
            return JsonResponse(dict(code=500, msg='出了点小问题，请尝试重新转换'))

    finally:
        driver.close()


@api_view()
def get_download_interval(request):
    return JsonResponse(dict(code=200, download_interval=settings.DOWNLOAD_INTERVAL))
