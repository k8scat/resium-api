# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""

import os

import django
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from downloader.models import Resource, User
from downloader.utils import aliyun_oss_get_file, get_file_md5


if __name__ == '__main__':

    resources = Resource.objects.filter(file_md5='').all()
    for resource in resources:
        file_md5 = get_file_md5(aliyun_oss_get_file(resource.key))
        resource.file_md5 = file_md5
        resource.save()




