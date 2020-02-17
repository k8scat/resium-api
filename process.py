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
from downloader.utils import aliyun_oss_delete_files


if __name__ == '__main__':

    resources = Resource.objects.all()
    admin = User.objects.get(email='hsowan.me@gmail.com', is_active=True)
    for resource in resources:
        resource.user = admin
        resource.save()




