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

from downloader.apis.resource import CsdnResource
from downloader.models import User, Resource
from downloader.utils import save_resource
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
                save_resource(url, filename, filepath, resource_info, user)
        else:
            print('文件不存在')
    else:
        print('资源已存在')


