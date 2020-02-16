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

    users = User.objects.all()
    fake = Faker('zh_CN')
    for user in users:
        user.nickname = fake.name()
        user.save()

    resources = Resource.objects.all()
    user = User.objects.get(email='hsowan.me@gmail.com', is_active=True)
    for resource in resources:
        resource.user = user
        resource.save()




