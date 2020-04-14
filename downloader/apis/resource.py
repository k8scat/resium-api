# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
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
from downloader.models import Resource, User, ResourceComment, DownloadRecord, CsdnAccount, DocerAccount, BaiduAccount, \
    DocerPreviewImage
from downloader.serializers import ResourceSerializers, ResourceCommentSerializers
from downloader.utils import aliyun_oss_upload, get_file_md5, ding, aliyun_oss_sign_url, \
    check_download, get_driver, check_oss, aliyun_oss_check_file, \
    save_resource, send_email, predict_code, get_random_ua


class BaseResource:
    def __init__(self, url, user):
        self.url = url
        self.user = user

    def before_download(self):
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
                    size = soup.select('strong.info_box span:nth-of-type(3) em')[0].text
                    resource = {
                        'title': soup.find('span', class_='resource_title').string,
                        'desc': soup.select('div.resource_description p')[0].text,
                        'tags': [tag.text for tag in soup.select('label.resource_tags a')],
                        'file_type': soup.select('dl.resource_box_dl dt img')[0]['src'].split('/')[-1].split('.')[0],
                        'point': point,
                        'size': size
                    }
                    return 200, resource
                except Exception as e:
                    ding('[CSDN] 资源信息解析失败',
                         error=e,
                         logger=logging.error,
                         user_email=self.user.email)
                    return 500, '资源获取失败'
            return

    def download(self, ret_url=False):
        self.before_download()

        try:
            csdn_account = CsdnAccount.objects.get(is_enabled=True)
            point = settings.CSDN_POINT
            # 可用积分不足
            if self.user.point < point:
                return 400, '积分不足，请进行捐赠'

            # 判断账号当天下载数
            if csdn_account.today_download_count >= 20:
                ding(f'[CSDN] 今日下载数已用完',
                     user_email=self.user.email,
                     resource_url=self.url,
                     used_account=csdn_account.email)
                return 403, '下载失败'
        except CsdnAccount.DoesNotExist:
            ding('[CSDN] 没有可用账号',
                 user_email=self.user.email,
                 resource_url=self.url)
            return 500, '下载失败'

        status, result = self.parse()
        if status != 200:
            return status, result
        resource = result
        if resource['point'] is None:
            ding('[CSDN] 用户尝试下载版权受限的资源',
                 user_email=self.user.email,
                 resource_url=self.url)
            return 400, '版权受限，无法下载'

        resource_id = self.url.split('/')[-1]
        headers = {
            'cookie': csdn_account.cookies,
            'user-agent': get_random_ua(),
            'referer': self.url  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
        }
        with requests.get(f'https://download.csdn.net/source/download?source_id={resource_id}',
                          headers=headers) as r:
            try:
                resp = r.json()
            except JSONDecodeError:
                ding('[CSDN] 下载失败',
                     error=r.text,
                     resource_url=self.url,
                     user_email=self.user.email,
                     used_account=csdn_account.email,
                     logger=logging.error)
                return 500, '下载失败'
            if resp['code'] == 200:
                # 更新账号今日下载数
                csdn_account.today_download_count += 1
                csdn_account.used_count += 1
                csdn_account.save()

                # 更新用户的剩余积分和已用积分
                self.user.point -= point
                self.user.used_point += point
                self.user.save()

                with requests.get(resp['data'], headers=headers, stream=True) as download_resp:
                    if download_resp.status_code == requests.codes.OK:
                        filename = parse.unquote(download_resp.headers['Content-Disposition'].split('"')[1])
                        filepath = os.path.join(self.save_dir, filename)
                        # 写入文件，用于线程上传资源到OSS
                        with open(filepath, 'wb') as f:
                            for chunk in download_resp.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        if ret_url:
                            download_url = save_resource(self.url, filename, filepath, resource, self.user,
                                                         account=csdn_account.email, ret_url=True)
                            return 200, dict(download_url=download_url, point=point)

                        # 上传资源到OSS并保存记录到数据库
                        t = Thread(target=save_resource,
                                   args=(self.url, filename, filepath, resource, self.user),
                                   kwargs={'account': csdn_account.email})
                        t.start()
                        return 200, dict(filepath=filepath, filename=filename)

                    ding('[CSDN] 下载失败',
                         error=download_resp.text,
                         user_email=self.user.email,
                         resource_url=self.url,
                         used_account=csdn_account.email,
                         logger=logging.error)
                    return 500, '下载失败'
            else:
                if resp.get('message', None) == '当前资源不开放下载功能':
                    return 400, 'CSDN未开放该资源的下载功能'

                ding('[CSDN] 下载失败',
                     error=resp,
                     user_email=self.user.email,
                     resource_url=self.url,
                     used_account=csdn_account.email,
                     logger=logging.error)
                return 500, '下载失败'


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

                    resource = {
                        'title': doc_info['docTitle'],
                        'tags': doc_info.get('newTagArray', []),
                        'desc': doc_info['docDesc'],
                        'file_type': file_type,
                        'point': point,
                        'wenku_type': wenku_type
                    }
                    return 200, resource
                except Exception as e:
                    ding(f'资源信息解析失败: {str(e)}',
                         resource_url=self.url,
                         user_email=self.user.email,
                         logger=logging.error)
                    return 500, '资源获取失败'
            else:
                return 500, '资源获取失败'

    def download(self, ret_url=False):
        self.before_download()

        status, result = self.parse()
        if status != 200:
            return status, result
        resource = result
        point = resource['point']
        if point is None:
            return 400, '该资源不支持下载'

        if self.user.point < point:
            return 400, '积分不足，请进行捐赠'

        try:
            baidu_account = BaiduAccount.objects.get(is_enabled=True)
        except BaiduAccount.DoesNotExist:
            ding('没有可用的百度文库账号',
                 user_email=self.user.email,
                 resource_url=self.url)
            return 500, '下载失败'
        driver = get_driver(self.unique_folder)
        try:
            driver.get('https://www.baidu.com/')
            # 添加cookies
            cookies = json.loads(baidu_account.cookies)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                driver.add_cookie(cookie)
            driver.get(self.url)
            wenku_type = resource['wenku_type']
            if wenku_type == 'VIP免费文档':
                baidu_account.vip_free_count += 1
            elif wenku_type == 'VIP专项文档':
                baidu_account.special_doc_count += 1
            elif wenku_type == '共享文档':
                baidu_account.share_doc_count += 1

            # 更新用户积分
            self.user.point -= point
            self.user.used_point += point
            self.user.save()
            baidu_account.save()

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
                if wenku_type != 'VIP专享文档':
                    # 已转存过此文档
                    download_button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, 'WkDialogOk'))
                    )
                    download_button.click()
                else:
                    ding('百度文库下载失败',
                         user_email=self.user.email,
                         used_account=baidu_account.email,
                         resource_url=self.url,
                         logger=logging.error)
                    return 500, '下载失败'

            filepath, filename = check_download(self.save_dir)

            if ret_url:
                download_url = save_resource(self.url, filename, filepath, resource, self.user,
                                             account=baidu_account.email, wenku_type=wenku_type, ret_url=True)
                return 200, dict(download_url=download_url, point=point)

            # 保存资源
            t = Thread(target=save_resource,
                       args=(self.url, filename, filepath, resource, self.user),
                       kwargs={'account': baidu_account.email, 'wenku_type': wenku_type})
            t.start()

            return 200, dict(filename=filename, filepath=filepath)
        except Exception as e:
            ding('[百度文库] 下载失败',
                 error=e,
                 user_email=self.user.email,
                 used_account=baidu_account.email,
                 resource_url=self.url)
            return 500, '下载失败'

        finally:
            driver.quit()


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

                resource = {
                    'title': soup.find('h1', class_='preview__title').string,
                    'tags': tags,
                    'file_type': soup.select('span.m-crumbs-path a')[0].text,
                    'desc': '',  # soup.find('meta', attrs={'name': 'Description'})['content']
                    'point': settings.DOCER_POINT,
                    'is_docer_vip_doc': r.text.count('类型：VIP模板') > 0,
                    'preview_images': preview_images
                }
                return 200, resource

            return 500, '资源获取失败'

    def download(self, ret_url=False):
        self.before_download()

        point = settings.DOCER_POINT
        if self.user.point < point:
            return 400, '积分不足，请进行捐赠'

        try:
            docer_account = DocerAccount.objects.get(is_enabled=True)
        except DocerAccount.DoesNotExist:
            ding('没有可以使用的稻壳VIP模板账号',
                 user_email=self.user.email,
                 resource_url=self.url,
                 logger=logging.error)
            return 500, '下载失败'

        # 下载资源
        resource_id = self.url.split('/')[-1]
        parse_url = f'https://www.docer.com/detail/dl?id={resource_id}'
        headers = {
            'cookie': docer_account.cookies,
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
                    docer_account.used_count += 1
                    docer_account.save()

                    download_url = resp['data']
                    filename = download_url.split('/')[-1]
                    filepath = os.path.join(self.save_dir, filename)
                    with requests.get(download_url, stream=True) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            with open(filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)

                            status, result = self.parse()
                            if status != 200:
                                return status, result
                            resource = result

                            if ret_url:
                                download_url = save_resource(self.url, filename, filepath, resource, self.user,
                                                             account=docer_account.email, is_docer_vip_doc=resource['is_docer_vip_doc'],
                                                             ret_url=True)
                                return 200, dict(download_url=download_url, point=point)

                            # 保存资源
                            t = Thread(target=save_resource,
                                       args=(self.url, filename, filepath, resource, self.user),
                                       kwargs={'account': docer_account.email, 'is_docer_vip_doc': resource['is_docer_vip_doc']})
                            t.start()

                            return 200, dict(filepath=filepath, filename=filename)

                        ding('[稻壳VIP模板] 下载失败',
                             error=download_resp.text,
                             user_email=self.user.email,
                             used_account=docer_account.email,
                             resource_url=self.url,
                             logger=logging.error)
                        return 500, '下载失败'
                else:
                    ding('[稻壳VIP模板] 下载失败',
                         error=r.text,
                         user_email=self.user.email,
                         resource_url=self.url,
                         logger=logging.error)
                    return 500, '下载失败'
            except JSONDecodeError:
                ding('[稻壳VIP模板] Cookies失效',
                     user_email=self.user.email,
                     resource_url=self.url,
                     logger=logging.error)
                return 500, '下载失败'


class ZhiwangResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
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

                    title = soup.select('div.wx-tit h1')[0].text
                    desc = soup.find('span', attrs={'id': 'ChDivSummary'}).string
                    has_pdf = True if soup.find('a', attrs={'id': 'pdfDown'}) else False
                    resource = {
                        'title': title,
                        'desc': desc,
                        'tags': tags,
                        'pdf_download': has_pdf,  # 是否支持pdf下载
                        'point': settings.ZHIWANG_POINT
                    }
                    return 200, resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         user_email=self.user.email,
                         resource_url=self.url)
                    return 500, '资源获取失败'
            else:
                return 500, '资源获取失败'

    def download(self, ret_url=False):
        self.before_download()

        point = settings.ZHIWANG_POINT
        if self.user.point < point:
            return 400, '积分不足，请进行捐赠'

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
                filepath, filename = check_download(self.save_dir)
                status, result = self.parse()
                if status != 200:
                    return status, result
                resource = result

                if ret_url:
                    download_url = save_resource(self.url, filename, filepath,
                                                 resource, self.user, ret_url=True)
                    return 200, dict(download_url=download_url, point=point)

                # 保存资源
                t = Thread(target=save_resource,
                           args=(self.url, filename, filepath, resource, self.user))
                t.start()

                self.user.point -= point
                self.user.used_point += point
                self.user.save()

                return 200, dict(filepath=filepath, filename=filename)

        except Exception as e:
            ding('[知网文献] 下载失败',
                 error=e,
                 user_email=self.user.email,
                 resource_url=self.url,
                 logger=logging.error)
            return 500, '下载失败'

        finally:
            driver.close()


@auth
@api_view(['POST'])
def upload(request):
    email = request.session.get('email')
    try:
        user = User.objects.get(email=email, is_active=True)
        if not user.phone:
            return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未认证'))

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

            # 发送邮件通知
            subject = '[源自下载] 资源上传成功'
            content = '您上传的资源将由管理员审核。如果审核通过，当其他用户下载该资源时，您将获得1积分奖励。'
            send_email(subject, content, user.email)

            ding(f'有新的资源上传 {key}')
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

    email = request.session.get('email')
    try:
        user = User.objects.get(email=email)
        resources = Resource.objects.order_by('-create_time').filter(user=user).all()
        return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view()
def get_resource(request):
    resource_id = request.GET.get('id', None)
    if resource_id:
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
            resource = ResourceSerializers(resource).data
            # todo: 可以尝试通过django-rest-framework实现，而不是手动去获取预览图的数据
            resource.setdefault('preview_images', preview_images)
            return JsonResponse(dict(code=200, resource=resource))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=404, msg='资源不存在'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view()
def list_comments(request):
    resource_id = request.GET.get('resource_id', None)
    if resource_id:
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
    resource_id = request.data.get('resource_id', None)
    user_id = request.data.get('user_id', None)
    if content and resource_id and user_id:
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
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    key = request.GET.get('key', '')
    if page < 1:
        page = 1

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

    email = request.session.get('email')
    if cache.get(email) and not settings.DEBUG:
        return JsonResponse(dict(code=403, msg='下载请求过快'), status=403)

    try:
        user = User.objects.get(email=email, is_active=True)
        if not user.phone:
            return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))
        if not user.can_download:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        cache.set(email, True, timeout=settings.DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未认证'))

    resource_url = request.data.get('url', None)
    if not resource_url:
        return JsonResponse(dict(code=400, msg='资源地址不能为空'))
    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    # 检查OSS是否存有该资源
    oss_resource = check_oss(resource_url)
    if oss_resource:
        point = request.data.get('point', None)
        if not point:
            return JsonResponse(dict(code=400, msg='错误的请求'))
        if user.point < point:
            return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

        # 判断用户是否下载过该资源
        # 若没有，则给上传资源的用户赠送积分
        if user != oss_resource.user:
            if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
                oss_resource.user.point += 1
                oss_resource.user.save()

        # 新增下载记录
        DownloadRecord(user=user,
                       resource=oss_resource,
                       download_device=user.login_device,
                       download_ip=user.login_ip,
                       used_point=point).save()
        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()

        # 生成临时下载地址
        url = aliyun_oss_sign_url(oss_resource.key)

        # 更新资源的下载次数
        oss_resource.download_count += 1
        oss_resource.save()

        return JsonResponse(dict(code=200, url=url))

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
    # 将资源存放的路径记录到日志
    logging.info(f'资源[{resource_url}]保存路径: {save_dir}')

    # CSDN资源下载
    if re.match(settings.PATTERN_CSDN, resource_url):
        resource = CsdnResource(resource_url, user)

    # 百度文库文档下载
    elif re.match(settings.PATTERN_WENKU, resource_url):
        resource = WenkuResource(resource_url, user)

    # 稻壳模板下载
    elif re.match(settings.PATTERN_DOCER, resource_url):
        resource = DocerResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        resource = ZhiwangResource(resource_url, user)

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    status, result = resource.download()
    if status != 200:
        return JsonResponse(dict(code=status, msg=result))

    response = FileResponse(open(result['filepath'], 'rb'))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(result['filename'],
                                                                            safe=string.printable) + '"'
    return response


@auth
@api_view()
def oss_download(request):
    """
    从OSS上下载资源
    """

    email = request.session.get('email')
    if cache.get(email):
        return JsonResponse(dict(code=403, msg='下载请求过快'), status=403)

    try:
        user = User.objects.get(email=email, is_active=True)
        if not user.phone:
            return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))

        cache.set(email, True, timeout=settings.DOWNLOAD_INTERVAL)
        point = settings.OSS_RESOURCE_POINT
        if user.point < point:
            return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未认证'))

    key = request.GET.get('key', None)
    if not key:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        oss_resource = Resource.objects.get(key=key)
        if not aliyun_oss_check_file(oss_resource.key):
            logging.error(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
            ding(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
            oss_resource.is_audited = 0
            oss_resource.save()
            return JsonResponse(dict(code=400, msg='该资源暂时无法下载'))
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=400, msg='资源不存在'))

    # 判断用户是否下载过该资源
    # 若没有，则给上传资源的用户赠送积分
    # 上传者下载自己的资源不会获得积分
    if user != oss_resource.user:
        if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
            oss_resource.user.point += 1
            oss_resource.user.save()

    DownloadRecord.objects.create(user=user,
                                  resource=oss_resource,
                                  download_device=user.login_device,
                                  download_ip=user.login_ip,
                                  used_point=settings.OSS_RESOURCE_POINT)

    # 更新用户积分
    user.point -= point
    user.used_point += point
    user.save()

    url = aliyun_oss_sign_url(oss_resource.key)
    oss_resource.download_count += 1
    oss_resource.save()
    return JsonResponse(dict(code=200, url=url))


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

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    email = request.session.get('email')
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return JsonResponse(dict(code=403, msg='未认证'))

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

    else:
        return JsonResponse(dict(code=400, msg='资源地址有误'))

    status, result = resource.parse()
    if status != 200:
        return JsonResponse(dict(code=status, msg=result))
    return JsonResponse(dict(code=status, resource=result))


@auth
@api_view(['POST'])
def check_resource_existed(request):
    url = request.data.get('url', None)
    if not url:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    is_resource_existed = Resource.objects.filter(url=url).count() > 0
    return JsonResponse(dict(code=200, is_existed=is_resource_existed))
