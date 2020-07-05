# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/6/23

手动上传CSDN资源

解析资源信息

上传本地文件

"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

from django.conf import settings

from downloader.apis.resource import CsdnResource
from downloader.models import User, Resource
from downloader.utils import save_resource, get_file_md5
import requests


if __name__ == '__main__':
    user = User.objects.get(uid='666666')
    url = input('请输入CSDN资源地址：').strip()
    if Resource.objects.filter(url=url).count() == 0:
        filename = input('请输入文件名：').strip()
        filepath = os.path.join('/Users/mac/Downloads', filename)
        if os.path.exists(filepath):
            csdn_resource = CsdnResource(url, user)
            status, resource_info = csdn_resource.parse()
            if status == requests.codes.ok:
                # 大文件
                # with open(filepath, 'rb') as f:
                #     file_md5 = get_file_md5(f)
                # # 资源文件大小
                # size = os.path.getsize(filepath)
                # # django的CharField可以直接保存list，会自动转成str
                # key = '0baec452-be84-11ea-8600-a0999b0715d5-mongodb-compass-1.18.0-win32-x64.zip'
                # resource = Resource.objects.create(title=resource_info['title'], filename=filename, size=size,
                #                                    url=url, key=key,
                #                                    tags=settings.TAG_SEP.join(resource_info['tags']),
                #                                    file_md5=file_md5, desc=resource_info['desc'], user=user,
                #                                    wenku_type=None,
                #                                    is_docer_vip_doc=False,
                #                                    local_path=filepath)

                # 小文件
                save_resource(url, filename, filepath, resource_info, user)
        else:
            print('文件不存在')
    else:
        print('资源已存在')


