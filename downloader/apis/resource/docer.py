import logging
import os
import uuid
from json import JSONDecodeError
from threading import Thread

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from downloader.apis.resource import BaseResource
from downloader.models import DocerPreviewImage, DocerAccount, PointRecord
from downloader.utils import save_resource, ding, get_random_ua, get_driver


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
