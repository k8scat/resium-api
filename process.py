# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

"""

import os

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from downloader.models import Resource
from downloader.utils import aliyun_oss_get_file, get_file_md5


if __name__ == '__main__':
    resources = Resource.objects.filter(file_md5='').all()
    for resource in resources:
        file = aliyun_oss_get_file(resource.key)
        file_md5 = get_file_md5(file)
        resource.file_md5 = file_md5
        resource.save()
        print(resource.file_md5)


