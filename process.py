# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""

import os

import django
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()

from downloader.models import Resource
from downloader.utils import aliyun_oss_delete_files


if __name__ == '__main__':

    resources = Resource.objects.all()
    keys = [resource.key for resource in resources]
    aliyun_oss_delete_files(keys)
    Resource.objects.all().delete()





