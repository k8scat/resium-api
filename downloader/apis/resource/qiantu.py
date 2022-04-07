import logging
import os
import uuid
from threading import Thread

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from downloader.apis.resource import BaseResource
from downloader.models import QiantuAccount, PointRecord
from downloader.utils import ding, get_random_ua, save_resource


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