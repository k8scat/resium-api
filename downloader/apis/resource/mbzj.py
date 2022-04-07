import logging
import os
import uuid
from threading import Thread

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from downloader.apis.resource import BaseResource
from downloader.models import MbzjAccount, PointRecord
from downloader.utils import get_random_ua, ding, save_resource


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