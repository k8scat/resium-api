# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
from threading import Thread
from time import sleep

from PIL import Image
from django.db.models import Q
from django.http import JsonResponse, FileResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.decorators import api_view
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.decorators import auth
from downloader.models import *
from downloader.serializers import ResourceSerializers, ResourceCommentSerializers, UploadRecordSerializers
from downloader.utils import *


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
        self.filename_uuid = None

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
                self.save_dir = os.path.join(
                    settings.DOWNLOAD_DIR, self.unique_folder)
            else:
                os.mkdir(self.save_dir)
                break

    def send_email(self, url):
        subject = '[源自下载] 资源下载成功'
        html_message = render_to_string(
            'downloader/download_url.html', {'url': url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[self.user.email],
                      html_message=html_message,
                      fail_silently=False)
            return requests.codes.ok, url
        except Exception as e:
            ding('资源下载地址邮件发送失败',
                 error=e,
                 uid=self.user.uid,
                 resource_url=self.url,
                 download_account_id=self.account.id,
                 logger=logging.error,
                 need_email=True)
            return requests.codes.server_error, '邮件发送失败'

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
                    copyright_limited = len(soup.select(
                        'div.resource_box a.copty-btn')) != 0
                    # 付费资源
                    need_pay = soup.select(
                        'div#downloadBtn span.va-middle')[0].text.find('¥') != -1
                    can_download = not copyright_limited and not need_pay
                    if can_download:
                        point = settings.CSDN_POINT
                    else:
                        point = None

                    info = soup.select('div.mt-16.t-c-second.line-h-1 span')
                    self.resource = {
                        'title': soup.find('h1', class_='el-tooltip d-ib title fs-xxl line-2').string.strip(),
                        'desc': soup.select('p.detail-desc')[0].text,
                        'tags': [tag.text for tag in soup.select('div.tags a')],
                        'file_type': info[2].text,
                        'point': point,
                        'size': info[3].text
                    }
                    return requests.codes.ok, self.resource
                except Exception as e:
                    ding('[CSDN] 资源信息解析失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         need_email=True)
                    return requests.codes.server_error, '资源获取失败'
            elif r.status_code == requests.codes.not_found:
                return requests.codes.not_found, '资源不存在，请检查资源地址是否正确'
            else:
                return requests.codes.server_error, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            cache.delete(settings.CSDN_DOWNLOADING_KEY)
            return status, result

        point = self.resource['point']
        if point is None:
            ding('[CSDN] 用户尝试下载版权受限的资源',
                 uid=self.user.uid,
                 resource_url=self.url)
            cache.delete(settings.CSDN_DOWNLOADING_KEY)
            return requests.codes.bad_request, '版权受限，无法下载'
        # 可用积分不足
        if self.user.point < point:
            cache.delete(settings.CSDN_DOWNLOADING_KEY)
            return 5000, '积分不足，请进行捐赠支持。'

        try:
            self.account = CsdnAccount.objects.get(is_enabled=True)

            # 判断账号当天下载数
            if self.account.today_download_count >= 20:
                ding(f'[CSDN] 今日下载数已用完',
                     uid=self.user.uid,
                     resource_url=self.url,
                     download_account_id=self.account.id,
                     need_email=True)
                # 自动切换CSDN
                self.account = switch_csdn_account(self.account)
                if not self.account:
                    cache.delete(settings.CSDN_DOWNLOADING_KEY)
                    return requests.codes.server_error, '下载失败，请联系管理员'
        except CsdnAccount.DoesNotExist:
            ding('[CSDN] 没有可用账号',
                 uid=self.user.uid,
                 resource_url=self.url,
                 need_email=True)
            cache.delete(settings.CSDN_DOWNLOADING_KEY)
            return requests.codes.server_error, '下载失败'

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
                         download_account_id=self.account.id,
                         logger=logging.error,
                         need_email=True)
                    cache.delete(settings.CSDN_DOWNLOADING_KEY)
                    return requests.codes.server_error, '下载失败'
                if resp['code'] == requests.codes.ok:
                    # 更新账号今日下载数
                    self.account.today_download_count += 1
                    self.account.used_count += 1
                    self.account.valid_count -= 1
                    self.account.save()

                    # 更新用户的剩余积分和已用积分
                    self.user.point -= point
                    self.user.used_point += point
                    self.user.save()
                    PointRecord(user=self.user, used_point=point,
                                point=self.user.point, comment='下载CSDN资源',
                                url=self.url).save()

                    with requests.get(resp['data'], headers=headers, stream=True) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            self.filename = parse.unquote(
                                download_resp.headers['Content-Disposition'].split('"')[1])
                            file = os.path.splitext(self.filename)
                            self.filename_uuid = str(uuid.uuid1()) + file[1]
                            self.filepath = os.path.join(
                                self.save_dir, self.filename_uuid)
                            # 写入文件，用于线程上传资源到OSS
                            with open(self.filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                            cache.delete(settings.CSDN_DOWNLOADING_KEY)
                            return requests.codes.ok, '下载成功'

                        ding('[CSDN] 下载失败',
                             error=download_resp.text,
                             uid=self.user.uid,
                             resource_url=self.url,
                             download_account_id=self.account.id,
                             logger=logging.error,
                             need_email=True)
                        cache.delete(settings.CSDN_DOWNLOADING_KEY)
                        return requests.codes.server_error, '下载失败'
                else:
                    if resp.get('message', None) == '当前资源不开放下载功能':
                        cache.delete(settings.CSDN_DOWNLOADING_KEY)
                        return requests.codes.bad_request, 'CSDN未开放该资源的下载功能'
                    elif resp.get('message', None) == '短信验证':
                        ding('[CSDN] 下载失败，需要短信验证',
                             error=resp,
                             uid=self.user.uid,
                             resource_url=self.url,
                             download_account_id=self.account.id,
                             logger=logging.error,
                             need_email=True)
                        # 自动切换CSDN
                        switch_result = switch_csdn_account(
                            self.account, need_sms_validate=True)
                        cache.delete(settings.CSDN_DOWNLOADING_KEY)
                        return requests.codes.server_error, '下载出了点小问题，请尝试重新下载' if switch_result else '下载失败，请联系管理员'

                    ding('[CSDN] 下载失败',
                         error=resp,
                         uid=self.user.uid,
                         resource_url=self.url,
                         download_account_id=self.account.id,
                         logger=logging.error,
                         need_email=True)
                    cache.delete(settings.CSDN_DOWNLOADING_KEY)
                    return requests.codes.server_error, '下载失败'
            else:
                ding('[CSDN] 下载失败',
                     error=r.text,
                     uid=self.user.uid,
                     resource_url=self.url,
                     download_account_id=self.account.id,
                     logger=logging.error,
                     need_email=True)
                cache.delete(settings.CSDN_DOWNLOADING_KEY)
                return requests.codes.server_error, '下载失败'

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 上传资源到OSS并保存记录到数据库
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath,
                         self.resource, self.user),
                   kwargs={'account_id': self.account.id})
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 上传资源到OSS并保存记录到数据库
        download_url = save_resource(resource_url=self.url, filename=self.filename,
                                     filepath=self.filepath, resource_info=self.resource,
                                     user=self.user, account_id=self.account.id,
                                     return_url=True)

        if use_email:
            return self.send_email(download_url)  # 这里也是返回status_code, url

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'


class WenkuResource(BaseResource):
    def __init__(self, url, user, doc_id):
        super().__init__(url, user)
        self.doc_id = doc_id

    def parse(self):
        """
        资源信息获取地址: https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id=
        """
        logging.info(f'百度文库文档ID: {self.doc_id}')

        get_doc_info_url = f'https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id={self.doc_id}'
        get_vip_free_doc_url = f'https://wenku.baidu.com/user/interface/getvipfreedoc?doc_id={self.doc_id}'
        headers = {
            'user-agent': get_random_ua()
        }
        with requests.get(get_doc_info_url, headers=headers, verify=False) as r:
            if r.status_code == requests.codes.OK:
                try:
                    data = json.loads(r.content.decode()[7:-1])
                    doc_info = data['docInfo']
                    # 判断是否是VIP专享文档
                    if doc_info.get('professionalDoc', None) == 1:
                        point = settings.WENKU_SPECIAL_DOC_POINT
                        wenku_type = 'VIP专项文档'
                    elif doc_info.get('isPaymentDoc', None) == 0:
                        with requests.get(get_vip_free_doc_url, headers=headers, verify=False) as _:
                            if _.status_code == requests.codes.OK and _.json()['status']['code'] == 0:
                                if _.json()['data']['is_vip_free_doc']:
                                    point = settings.WENKU_VIP_FREE_DOC_POINT
                                    wenku_type = 'VIP免费文档'
                                else:
                                    point = settings.WENKU_SHARE_DOC_POINT
                                    wenku_type = '共享文档'
                            else:
                                return requests.codes.server_error, '资源获取失败'
                    else:
                        point = None
                        wenku_type = '付费文档'

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
                             error=doc_info,
                             need_email=True)
                        file_type = 'UNKNOWN'

                    self.resource = {
                        'title': doc_info['docTitle'],
                        'tags': doc_info.get('newTagArray', []),
                        'desc': doc_info['docDesc'],
                        'file_type': file_type,
                        'point': point,
                        'wenku_type': wenku_type
                    }
                    return requests.codes.ok, self.resource
                except Exception as e:
                    ding(f'资源信息解析失败: {str(e)}',
                         resource_url=self.url,
                         uid=self.user.uid,
                         logger=logging.error,
                         need_email=True)
                    return requests.codes.server_error, '资源获取失败'
            else:
                return requests.codes.server_error, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            return status, result

        point = self.resource['point']
        if point is None:
            return requests.codes.bad_request, '该资源不支持下载'

        if self.user.point < point:
            return 5000, '积分不足，请进行捐赠支持。'

        # 更新用户积分
        self.user.point -= point
        self.user.used_point += point
        self.user.save()
        PointRecord(user=self.user, point=self.user.point,
                    comment='下载百度文库文档', url=self.url,
                    used_point=point).save()

        data = {
            "url": self.url
        }
        headers = {
            "token": settings.DOWNHUB_TOKEN
        }
        with requests.post(f'{settings.DOWNHUB_SERVER}/parse/wenku', json=data, headers=headers) as r:
            if r.status_code == requests.codes.ok:
                download_url = r.json().get('data', None)
                if not download_url:
                    ding('[百度文库] DownHub下载链接获取失败',
                         error=r.text,
                         logger=logging.error,
                         resource_url=self.url,
                         need_email=True)
                    return requests.codes.server_error, '下载失败'
                for queryItem in parse.urlparse(parse.unquote(download_url)).query.replace(' ', '').split(';'):
                    if re.match(r'^filename=".*"$', queryItem):
                        self.filename = queryItem.split('"')[1]
                        break
                    else:
                        continue
                if not self.filename:
                    ding('[百度文库] 文件名解析失败',
                         error=download_url,
                         logger=logging.error,
                         resource_url=self.url,
                         need_email=True)
                    return requests.codes.server_error, '下载失败'
                file = os.path.splitext(self.filename)
                self.filename_uuid = str(uuid.uuid1()) + file[1]
                self.filepath = os.path.join(self.save_dir, self.filename_uuid)
                with requests.get(download_url, stream=True) as download_resp:
                    if download_resp.status_code == requests.codes.OK:
                        with open(self.filepath, 'wb') as f:
                            for chunk in download_resp.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)

                        return requests.codes.ok, '下载成功'

                    ding('[百度文库] 下载失败',
                         error=download_resp.text,
                         uid=self.user.uid,
                         resource_url=self.url,
                         logger=logging.error,
                         need_email=True)
                    return requests.codes.server_error, '下载失败'
            else:
                return requests.codes.server_error, "下载失败"

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user))
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filepath=self.filepath, filename=self.filename,
                                     user=self.user, return_url=True)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'


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
                tags = [tag.text for tag in soup.select(
                    'li.preview__labels-item.g-link a')]
                if '展开更多' in tags:
                    tags = tags[:-1]

                # 获取所有的预览图片
                preview_images = DocerPreviewImage.objects.filter(
                    resource_url=self.url).all()
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
                                (By.XPATH,
                                 '//ul[@class="preview__img-list"]//img')
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
                        DocerPreviewImage.objects.bulk_create(
                            preview_image_models)
                    finally:
                        driver.close()

                self.resource = {
                    'title': soup.find('h1', class_='preview-info_title').string,
                    'tags': tags,
                    'file_type': soup.select('span.m-crumbs-path a')[0].text,
                    # soup.find('meta', attrs={'name': 'Description'})['content']
                    'desc': '',
                    'point': settings.DOCER_POINT,
                    'is_docer_vip_doc': r.text.count('类型：VIP模板') > 0,
                    'preview_images': preview_images
                }
                return requests.codes.ok, self.resource

            return requests.codes.server_error, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            return status, result

        point = self.resource['point']
        if self.user.point < point:
            return 5000, '积分不足，请进行捐赠支持。'

        try:
            self.account = DocerAccount.objects.get(is_enabled=True)
        except DocerAccount.DoesNotExist:
            ding('没有可以使用的稻壳VIP模板账号',
                 uid=self.user.uid,
                 resource_url=self.url,
                 logger=logging.error,
                 need_email=True)
            return requests.codes.server_error, '下载失败'

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
                    PointRecord(user=self.user, used_point=point,
                                comment='下载稻壳模板', url=self.url,
                                point=self.user.point).save()

                    # 更新账号使用下载数
                    self.account.used_count += 1
                    self.account.save()

                    download_url = resp['data']
                    self.filename = download_url.split('/')[-1]
                    file = os.path.splitext(self.filename)
                    self.filename_uuid = str(uuid.uuid1()) + file[1]
                    self.filepath = os.path.join(
                        self.save_dir, self.filename_uuid)
                    with requests.get(download_url, stream=True) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            with open(self.filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)

                            return requests.codes.ok, '下载成功'

                        ding('[稻壳VIP模板] 下载失败',
                             error=download_resp.text,
                             uid=self.user.uid,
                             download_account_id=self.account.id,
                             resource_url=self.url,
                             logger=logging.error,
                             need_email=True)
                        return requests.codes.server_error, '下载失败'
                else:
                    ding('[稻壳VIP模板] 下载失败',
                         error=r.text,
                         uid=self.user.uid,
                         resource_url=self.url,
                         logger=logging.error,
                         need_email=True)
                    return requests.codes.server_error, '下载失败'
            except JSONDecodeError:
                ding('[稻壳VIP模板] Cookies失效',
                     uid=self.user.uid,
                     resource_url=self.url,
                     logger=logging.error,
                     need_email=True)
                return requests.codes.server_error, '下载失败'

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath,
                         self.resource, self.user),
                   kwargs={'account_id': self.account.id})
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filename=self.filename, filepath=self.filepath,
                                     user=self.user, account_id=self.account.id,
                                     return_url=True)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'


class MbzjResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        headers = {
            'referer': 'http://www.cssmoban.com/',
            'user-agent': get_random_ua()
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.content.decode(), 'lxml')
                if self.url.count('wpthemes') > 0:
                    tags = [tag.text for tag in soup.select('div.tags a')]
                else:
                    tags = [tag.text for tag in soup.select('div.tags a')[:-1]]

                self.resource = {
                    'title': soup.select('div.con-right h1')[0].text,
                    'tags': tags,
                    'desc': '',
                    'point': settings.MBZJ_POINT,
                }
                return requests.codes.ok, self.resource

            return requests.codes.server_error, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            return status, result

        point = self.resource['point']
        if self.user.point < point:
            return 5000, '积分不足，请进行捐赠支持。'

        try:
            self.account = MbzjAccount.objects.get(is_enabled=True)
        except MbzjAccount.DoesNotExist:
            ding('没有可以使用的模板之家账号',
                 uid=self.user.uid,
                 resource_url=self.url,
                 logger=logging.error,
                 need_email=True)
            return requests.codes.server_error, '下载失败'

        # 下载资源
        resource_id = self.url.split('/')[-1].split('.shtml')[0]
        download_url = 'http://vip.cssmoban.com/api/Down'
        data = {
            'userid': self.account.user_id,
            'screkey': self.account.secret_key,
            'mobanid': resource_id
        }
        headers = {
            'referer': self.url,
            'user-agent': get_random_ua()
        }
        with requests.get(download_url, headers=headers, data=data) as r:
            resp = r.json()
            if resp['code'] == 0:
                # 更新用户积分
                self.user.point -= point
                self.user.used_point += point
                self.user.save()
                PointRecord(user=self.user, used_point=point,
                            comment='下载模板之家模板', url=self.url,
                            point=self.user.point).save()

                download_url = resp['data']
                self.filename = resp['data'].split('/')[-1]
                file = os.path.splitext(self.filename)
                self.filename_uuid = str(uuid.uuid1()) + file[1]
                self.filepath = os.path.join(self.save_dir, self.filename_uuid)
                with requests.get(download_url, stream=True) as download_resp:
                    if download_resp.status_code == requests.codes.OK:
                        with open(self.filepath, 'wb') as f:
                            for chunk in download_resp.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)

                        return requests.codes.ok, '下载成功'

                    ding('[模板之家] 下载失败',
                         error=download_resp.text,
                         uid=self.user.uid,
                         download_account_id=self.account.id,
                         resource_url=self.url,
                         logger=logging.error,
                         need_email=True)
                    return requests.codes.server_error, '下载失败'
            else:
                ding('[模板之家] 下载失败',
                     error=r.text,
                     uid=self.user.uid,
                     resource_url=self.url,
                     logger=logging.error,
                     need_email=True)
                return requests.codes.server_error, '下载失败'

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath,
                         self.resource, self.user),
                   kwargs={'account_id': self.account.id})
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filename=self.filename, filepath=self.filepath,
                                     user=self.user, account_id=self.account.id,
                                     return_url=True)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'


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
                    desc = soup.find(
                        'span', attrs={'id': 'ChDivSummary'}).string
                    has_pdf = True if soup.find(
                        'a', attrs={'id': 'pdfDown'}) else False
                    self.resource = {
                        'title': title,
                        'desc': desc,
                        'tags': tags,
                        'pdf_download': has_pdf,  # 是否支持pdf下载
                        'point': settings.ZHIWANG_POINT
                    }
                    return requests.codes.ok, self.resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         resource_url=self.url,
                         need_email=True)
                    return requests.codes.server_error, '资源获取失败'
            else:
                return requests.codes.server_error, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            return status, result

        point = self.resource['point']
        if self.user.point < point:
            return 5000, '积分不足，请进行捐赠支持。'

        # url = resource_url.replace('https://kns.cnki.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn')
        vpn_url = re.sub(r'http(s)?://kns(8)?\.cnki\.net',
                         'http://kns-cnki-net.wvpn.ncu.edu.cn', self.url)

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
                    (By.XPATH,
                     "//div[@class='col-md-6 col-md-offset-6 login-btn']/input")
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
                return requests.codes.bad_request, '该文献不支持下载PDF'

            self.user.point -= point
            self.user.used_point += point
            self.user.save()
            PointRecord(user=self.user, used_point=point,
                        comment='下载知网文献', url=self.url,
                        point=self.user.point).save()

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
                driver.get_screenshot_as_file(
                    settings.ZHIWANG_SCREENSHOT_IMAGE)

                # 手动设置截取位置
                left = 430
                upper = 275
                right = 620
                lower = 340
                # 通过Image处理图像
                img = Image.open(settings.ZHIWANG_SCREENSHOT_IMAGE)
                # 剪切图片
                img = img.crop((left, upper, right, lower))
                # 保存剪切好的图片
                img.save(settings.ZHIWANG_CODE_IMAGE)

                code = predict_code(settings.ZHIWANG_CODE_IMAGE)
                if code:
                    code_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, 'vcode')
                        )
                    )
                    code_input.send_keys(code)
                    submit_code_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH,
                             "//dl[@class='c_verify-code']/dd/button")
                        )
                    )
                    submit_code_button.click()
                else:
                    return requests.codes.server_error, '下载失败'

            finally:
                status, result = check_download(self.save_dir)
                if status == requests.codes.ok:
                    self.filename = result
                    file = os.path.splitext(self.filename)
                    self.filename_uuid = str(uuid.uuid1()) + file[1]
                    self.filepath = os.path.join(
                        self.save_dir, self.filename_uuid)
                    return requests.codes.ok, '下载成功'
                else:
                    return status, result

        except Exception as e:
            ding('[知网文献] 下载失败',
                 error=e,
                 uid=self.user.uid,
                 resource_url=self.url,
                 logger=logging.error,
                 need_email=True)
            return requests.codes.server_error, '下载失败'

        finally:
            driver.close()

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user))
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filepath=self.filepath, filename=self.filename,
                                     user=self.user, return_url=True)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'


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
                    tags = [tag.string for tag in soup.select(
                        'div.mainRight-tagBox a')]
                    self.resource = {
                        'title': title,
                        'size': size,
                        'tags': tags,
                        'desc': '',
                        'file_type': file_type,
                        'point': settings.QIANTU_POINT
                    }
                    return requests.codes.ok, self.resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         resource_url=self.url,
                         need_email=True)
                    return requests.codes.server_error, "资源获取失败"

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            return status, result
        point = self.resource['point']
        if self.user.point < point:
            return 5000, '积分不足，请进行捐赠支持。'

        try:
            self.account = QiantuAccount.objects.get(is_enabled=True)
        except QiantuAccount.DoesNotExist:
            return requests.codes.server_error, "[千图网] 没有可用账号"

        headers = {
            'cookie': self.account.cookies,
            'referer': self.url,
            'user-agent': get_random_ua()
        }
        download_url = self.url.replace(
            'https://www.58pic.com/newpic/', 'https://dl.58pic.com/')
        with requests.get(download_url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    download_url = soup.select(
                        'a.clickRecord.autodown')[0]['href']
                    self.filename = download_url.split('?')[0].split('/')[-1]
                    file = os.path.splitext(self.filename)
                    self.filename_uuid = str(uuid.uuid1()) + file[1]
                    self.filepath = os.path.join(
                        self.save_dir, self.filename_uuid)
                    with requests.get(download_url, stream=True, headers=headers) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            self.user.point -= point
                            self.user.used_point += point
                            self.user.save()
                            PointRecord(user=self.user, used_point=point,
                                        comment='下载千图网资源', url=self.url,
                                        point=self.user.point).save()

                            with open(self.filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)

                            return requests.codes.ok, '下载成功'

                        ding('[千图网] 下载失败',
                             error=download_resp.text,
                             uid=self.user.uid,
                             download_account_id=self.account.id,
                             resource_url=self.url,
                             logger=logging.error,
                             need_email=True)
                        return requests.codes.server_error, '下载失败'
                except Exception as e:
                    ding('[千图网] 下载失败',
                         error=e,
                         uid=self.user.uid,
                         resource_url=self.url,
                         logger=logging.error,
                         download_account_id=self.account.id,
                         need_email=True)
                    return requests.codes.server_error, "下载失败"

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath,
                         self.resource, self.user),
                   kwargs={'account_id': self.account.id})
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filename=self.filename, filepath=self.filepath,
                                     user=self.user, account_id=self.account.id,
                                     return_url=True)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'


@auth
@api_view(['POST'])
def upload(request):
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg='未登录'))

    file = request.FILES.get('file', None)
    if not file:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    if file.size > (2 * 10) * 1024 * 1024:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='上传资源大小不能超过20MiB'))

    file_md5 = get_file_md5(file.open('rb'))
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=requests.codes.bad_request, msg='资源已存在'))

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
            resource = Resource.objects.create(title=title, desc=desc, tags=tags,
                                               filename=filename, size=file.size,
                                               download_count=0, is_audited=0, key=key,
                                               user=user, file_md5=file_md5, local_path=filepath)

            UploadRecord(user=user, resource=resource).save()

            # 开线程上传资源到OSS
            t = Thread(target=aliyun_oss_upload, args=(filepath, key))
            t.start()

            ding(f'有新的资源上传 {key}',
                 uid=user.uid)
            return JsonResponse(dict(code=requests.codes.ok, msg='资源上传成功'))
        except Exception as e:
            logging.error(e)
            ding(f'资源上传失败: {str(e)}',
                 need_email=True)
            return JsonResponse(dict(code=requests.codes.server_error, msg='资源上传失败'))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))


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
        return JsonResponse(dict(code=requests.codes.bad_request, msg='资源已存在'))
    return JsonResponse(dict(code=requests.codes.ok, msg='资源不存在'))


@auth
@api_view()
def list_uploaded_resources(request):
    """
    获取用户上传资源

    :param request:
    :return:
    """

    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)
    upload_records = UploadRecord.objects.filter(
        user=user).order_by('-create_time').all()
    return JsonResponse(dict(code=requests.codes.ok, resources=UploadRecordSerializers(upload_records, many=True).data))


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
            resource_.setdefault(
                'point', settings.OSS_RESOURCE_POINT + resource.download_count - 1)
            return JsonResponse(dict(code=requests.codes.ok, resource=resource_))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=404, msg='资源不存在'))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))


@api_view()
def list_resource_comments(request):
    resource_id = request.GET.get('id', None)
    if not resource_id:
        return JsonResponse(dict(code=requests.codes.bad_request,
                                 msg='错误的请求'))

    try:
        resource = Resource.objects.get(id=resource_id)
        comments = ResourceComment.objects.filter(
            resource=resource).order_by('-create_time').all()
        return JsonResponse(dict(code=requests.codes.ok,
                                 comments=ResourceCommentSerializers(comments, many=True).data))
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found,
                                 msg='资源不存在'))


@auth
@api_view(['POST'])
def create_resource_comment(request):
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    content = request.data.get('content', None)
    resource_id = request.data.get('id', None)
    if not content or not resource_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        resource = Resource.objects.get(id=resource_id, is_audited=1)
        resource_comment = ResourceComment.objects.create(
            user=user, resource=resource, content=content)
        return JsonResponse(dict(code=requests.codes.ok,
                                 msg='评论成功',
                                 comment=ResourceCommentSerializers(resource_comment).data))
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='资源不存在'))


@api_view()
def list_resources(request):
    """
    分页获取资源
    """

    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        page = int(page)
        if page < 1:
            page = 1

        per_page = int(per_page)
        if per_page > 20:
            per_page = 20
    except ValueError:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    key = request.GET.get('key', '')

    start = per_page * (page - 1)
    end = start + per_page
    # https://cloud.tencent.com/developer/ask/81558
    resources = Resource.objects.filter(Q(is_audited=1),
                                        Q(title__icontains=key) |
                                        Q(desc__icontains=key) |
                                        Q(tags__icontains=key)).order_by('-create_time').all()[start:end]
    return JsonResponse(dict(code=requests.codes.ok, resources=ResourceSerializers(resources, many=True).data))


@api_view()
def get_resource_count(request):
    """
    获取资源的数量
    """
    key = request.GET.get('key', '')
    return JsonResponse(dict(code=requests.codes.ok, count=Resource.objects.filter(Q(is_audited=1),
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

    return JsonResponse(
        dict(code=requests.codes.ok, tags=settings.TAG_SEP.join(random.sample(ret_tags, settings.SAMPLE_TAG_COUNT))))


@auth
@api_view(['POST'])
def download(request):
    """
    资源下载

    参数:
    url
    t
    point
    """

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
        if cache.get(uid) and not settings.DEBUG:
            return JsonResponse(dict(code=requests.codes.forbidden, msg='请求频率过快，请稍后再试！'))
        if not user.is_admin and not user.can_download:
            return JsonResponse(dict(code=requests.codes.bad_request, msg='未授权'))

        if not user.is_admin:
            cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg='未登录'))

    resource_url = request.data.get('url', None)
    # 下载返回类型（不包括直接在OSS找到的资源），file/url/email，默认file
    downloadType = request.data.get('t', 'file')
    if downloadType == 'email' and not user.email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='账号未设置邮箱'))

    if not resource_url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='资源地址不能为空'))

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    if re.match(settings.PATTERN_MBZJ, resource_url):
        resource_url = re.sub(r'\.shtml.*', '.shtml', resource_url)

    doc_id = None
    if re.match(settings.PATTERN_WENKU, resource_url):
        resource_url, doc_id = get_wenku_doc_id(resource_url)

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
                    (re.match(settings.PATTERN_ITEYE, resource_url) and point != settings.ITEYE_POINT) or \
                    (re.match(settings.PATTERN_MBZJ, resource_url) and point != settings.MBZJ_POINT):
                cache.delete(user.uid)
                return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

            if user.point < point:
                cache.delete(user.uid)
                return JsonResponse(dict(code=5000, msg='积分不足，请进行捐赠支持。'))

        # 新增下载记录
        DownloadRecord(user=user,
                       resource=oss_resource,
                       used_point=point).save()

        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()
        PointRecord(user=user, used_point=point,
                    comment='下载资源', url=resource_url,
                    point=user.point).save()

        # 生成临时下载地址，10分钟有效
        url = aliyun_oss_sign_url(oss_resource.key)

        # 更新资源的下载次数
        oss_resource.download_count += 1
        oss_resource.save()

        if downloadType == 'email':
            subject = '[源自下载] 资源下载成功'
            html_message = render_to_string(
                'downloader/download_url.html', {'url': url})
            plain_message = strip_tags(html_message)
            try:
                send_mail(subject=subject,
                          message=plain_message,
                          from_email=settings.DEFAULT_FROM_EMAIL,
                          recipient_list=[user.email],
                          html_message=html_message,
                          fail_silently=False)
                return JsonResponse(dict(code=requests.codes.ok, msg='下载成功，请前往邮箱查收！（如果未收到邮件，请检查是否被收入垃圾箱！）', url=url))
            except Exception as e:
                ding('资源下载地址邮件发送失败',
                     error=e,
                     uid=user.uid,
                     logger=logging.error,
                     need_email=True)
                return JsonResponse(dict(code=requests.codes.server_error, msg='邮件发送失败'))

        return JsonResponse(dict(code=requests.codes.ok, url=url))

    ding('正在下载',
         resource_url=resource_url,
         uid=uid)

    # CSDN资源下载
    if re.match(settings.PATTERN_CSDN, resource_url):
        if cache.get(settings.CSDN_DOWNLOADING_KEY):
            return JsonResponse(dict(code=requests.codes.forbidden, msg='当前下载人数过多，请稍后再尝试下载！'))
        cache.set(settings.CSDN_DOWNLOADING_KEY, True,
                  settings.CSDN_DOWNLOADING_MAX_TIME)

        resource = CsdnResource(resource_url, user)

    elif re.match(settings.PATTERN_ITEYE, resource_url):
        resource_url = 'https://download.csdn.net/download/' + \
            resource_url.split('resource/')[1].replace('-', '/')
        resource = CsdnResource(resource_url, user)

    # 百度文库文档下载
    elif re.match(settings.PATTERN_WENKU, resource_url):
        if not doc_id:
            ding('[百度文库] 资源地址正则通过，但没有doc_id',
                 resource_url=resource_url)
            return JsonResponse(dict(code=requests.codes.bad_request, msg='资源地址有误'))
        else:
            resource = WenkuResource(resource_url, user, doc_id)

    # 稻壳模板下载
    elif re.match(settings.PATTERN_DOCER, resource_url):
        if resource_url.count('webmall') > 0:
            resource_url = resource_url.replace('/webmall', '')
        resource = DocerResource(resource_url, user)

    elif re.match(settings.PATTERN_QIANTU, resource_url):
        resource = QiantuResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        resource = ZhiwangResource(resource_url, user)

    elif re.match(settings.PATTERN_MBZJ, resource_url):
        resource = MbzjResource(resource_url, user)

    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    if downloadType == 'file':
        status, result = resource.get_filepath()
        if status != requests.codes.ok:  # 下载失败
            cache.delete(user.uid)
            return JsonResponse(dict(code=status, msg=result))

        response = FileResponse(open(result['filepath'], 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="' + parse.quote(result['filename'],
                                                                                safe=string.printable) + '"'
        return response

    elif downloadType == 'url':
        status, result = resource.get_filepath()
        if status != requests.codes.ok:  # 下载失败
            cache.delete(user.uid)
            return JsonResponse(dict(code=status, msg=result))

        return JsonResponse(dict(code=status, url=result['download_url']))

    elif downloadType == 'email':
        status, result = resource.get_url(use_email=True)
        if status != requests.codes.ok:  # 下载失败
            cache.delete(user.uid)
            return JsonResponse(dict(code=status, msg=result))

        return JsonResponse(dict(code=status, msg='下载成功，请前往邮箱查收！（如果未收到邮件，请检查是否被收入垃圾箱！）', url=result))

    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))


@auth
@api_view()
def oss_download(request):
    """
    从OSS上下载资源
    """

    uid = request.session.get('uid')
    if cache.get(uid):
        return JsonResponse(dict(code=requests.codes.forbidden, msg='请求频率过快，请稍后再试！'))

    user = User.objects.get(uid=uid)
    cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)

    t = request.GET.get('t', 'url')

    resource_id = request.GET.get('id', None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
    else:
        cache.delete(user.uid)
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        oss_resource = Resource.objects.get(id=resource_id)
        if not aliyun_oss_check_file(oss_resource.key):
            logging.error(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
            ding(f'OSS资源不存在，请及时检查资源 {oss_resource.key}',
                 uid=user.uid,
                 logger=logging.error,
                 need_email=True)
            oss_resource.is_audited = 0
            oss_resource.save()
            cache.delete(user.uid)
            return JsonResponse(dict(code=requests.codes.bad_request, msg='该资源暂时无法下载'))
    except Resource.DoesNotExist:
        cache.delete(user.uid)
        return JsonResponse(dict(code=requests.codes.not_found, msg='资源不存在'))

    point = settings.OSS_RESOURCE_POINT + oss_resource.download_count - 1
    if user.point < point:
        cache.delete(user.uid)
        return JsonResponse(dict(code=5000, msg='积分不足，请进行捐赠支持。'))

    user.point -= point
    user.used_point += point
    user.save()
    PointRecord(user=user, point=user.point,
                comment='下载资源', used_point=point,
                resource=oss_resource).save()
    DownloadRecord.objects.create(user=user,
                                  resource=oss_resource,
                                  used_point=settings.OSS_RESOURCE_POINT)

    url = aliyun_oss_sign_url(oss_resource.key)
    oss_resource.download_count += 1
    oss_resource.save()

    if t == 'url':
        return JsonResponse(dict(code=requests.codes.ok, url=url))
    elif t == 'email':
        if not user.email:
            return JsonResponse(dict(code=requests.codes.bad_request, msg='未设置邮箱'))

        subject = '[源自下载] 资源下载成功'
        html_message = render_to_string(
            'downloader/download_url.html', {'url': url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[user.email],
                      html_message=html_message,
                      fail_silently=False)
            return JsonResponse(dict(code=requests.codes.ok, url=url, msg='下载成功，请前往邮箱查收！（如果未收到邮件，请检查是否被收入垃圾箱！）'))
        except Exception as e:
            ding('资源下载地址邮件发送失败',
                 error=e,
                 uid=user.uid,
                 logger=logging.error,
                 need_email=True)
            return JsonResponse(dict(code=requests.codes.server_error, msg='邮件发送失败'))


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
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    logging.info(resource_url)

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

    doc_id = None
    if re.match(settings.PATTERN_WENKU, resource_url):
        resource_url, doc_id = get_wenku_doc_id(resource_url)

    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)

    # CSDN资源
    if re.match(settings.PATTERN_CSDN, resource_url):
        resource = CsdnResource(resource_url, user)

    elif re.match(settings.PATTERN_ITEYE, resource_url):
        resource_url = 'https://download.csdn.net/download/' + \
            resource_url.split('resource/')[1].replace('-', '/')
        resource = CsdnResource(resource_url, user)

    # 百度文库文档
    elif re.match(settings.PATTERN_WENKU, resource_url):
        resource = WenkuResource(resource_url, user, doc_id)

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

    elif re.match(settings.PATTERN_MBZJ, resource_url):
        resource = MbzjResource(resource_url, user)

    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='资源地址有误'))

    status, result = resource.parse()
    return JsonResponse(dict(code=status, resource=result))


@auth
@api_view(['POST'])
def check_resource_existed(request):
    url = request.data.get('url', None)
    if not url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    is_resource_existed = Resource.objects.filter(url=url).count() > 0
    return JsonResponse(dict(code=requests.codes.ok, is_existed=is_resource_existed))


@auth
@api_view(['POST'])
def doc_convert(request):
    command = request.POST.get('c', None)
    file = request.FILES.get('file', None)
    if not command or not file:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

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
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
        point = settings.DOC_CONVERT_POINT
        if user.point < point:
            return JsonResponse(dict(code=5000, msg='积分不足，请进行捐赠支持。'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg='未登录'))

    if file.size > 100 * 1000 * 1000:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='上传资源大小不能超过100MB'))

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
                EC.presence_of_element_located(
                    (By.XPATH, "//p[@class='converterNameV']"))
            )
            download_url = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[@class='dwon-document']"))
            ).get_attribute('href')
            # 保存文档转换记录
            DocConvertRecord(user=user, download_url=download_url,
                             point=point).save()
            # 更新用户积分
            user.point -= point
            user.used_point += point
            user.save()
            PointRecord(user=user, used_point=point,
                        point=user.point, comment='文档转换').save()
            ding(f'[文档转换] 转换成功，{download_url}',
                 uid=user.uid)
            return JsonResponse(dict(code=requests.codes.ok, url=download_url))
        except TimeoutException:
            DocConvertRecord(user=user).save()
            ding(f'[文档转换] 转换失败，{command}，{filepath}',
                 need_email=True)
            return JsonResponse(dict(code=requests.codes.server_error, msg='出了点小问题，请尝试重新转换'))

    finally:
        driver.close()


@api_view()
def get_download_interval(request):
    """
    获取下载间隔

    :param request:
    :return:
    """

    return JsonResponse(dict(code=requests.codes.ok, download_interval=settings.DOWNLOAD_INTERVAL))


@api_view(['POST'])
def check_docer_existed(request):
    token = request.data.get('token', '')
    if token != settings.ADMIN_TOKEN:
        return JsonResponse(dict(code=requests.codes.forbidden))

    docer_url = request.data.get('url', '')
    if re.match(settings.PATTERN_DOCER, docer_url):
        if docer_url.count('/webmall') > 0:
            docer_url = docer_url.replace('/webmall', '')
        docer_existed = Resource.objects.filter(url=docer_url).count() > 0
        return JsonResponse(dict(code=requests.codes.ok, existed=docer_existed))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request))
