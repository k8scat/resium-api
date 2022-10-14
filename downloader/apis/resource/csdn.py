import logging
import os
import uuid
from json import JSONDecodeError
from threading import Thread
from urllib import parse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache

from downloader.apis.resource import BaseResource
from downloader.models import CsdnAccount, PointRecord
from downloader.utils import get_random_ua, ding, switch_csdn_account, save_resource


class CsdnResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def _need_pay(self, soup: BeautifulSoup) -> bool:
        """
        判断是否是付费资源
        """
        items = soup.select('div#downloadBtn span.va-middle')
        if len(items) == 0:
            return False
        return items[0].text.find('¥') != -1

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
                    copyright_limited = len(soup.select('div.resource_box a.copty-btn')) != 0
                    need_pay = self._need_pay(soup)
                    can_download = not copyright_limited and not need_pay
                    if can_download:
                        point = settings.CSDN_POINT
                    else:
                        point = None

                    info = soup.select('div.info-box span')
                    if len(info) == 12:
                        size = info[9].text
                        file_type = info[10].text
                    elif len(info) == 11:
                        size = info[8].text
                        file_type = info[9].text
                    else:
                        ding('解析CSDN资源页面出错', resource_url=self.url,
                             logger=logging.error)
                        return requests.codes.server_error, '资源获取失败'

                    tags = soup.select('div.tags a')
                    title = soup.find('h1', class_='el-tooltip d-i fs-xxl line-2 va-middle').text.strip()
                    desc = soup.select('p.detail-desc')[0].text
                    self.resource = {
                        'title': title,
                        'desc': desc,
                        'tags': [tag.text for tag in tags],
                        'file_type': file_type,
                        'point': point,
                        'size': size,
                        'need_pay': need_pay,
                        'copyright_limited': copyright_limited
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
