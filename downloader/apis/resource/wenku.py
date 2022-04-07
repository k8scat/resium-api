import json
import logging
import os
import re
import uuid
from threading import Thread
from urllib import parse

import requests
from django.conf import settings

from downloader.apis.resource import BaseResource
from downloader.models import PointRecord
from downloader.utils import get_random_ua, ding, save_resource


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