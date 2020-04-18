# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()
from django.utils import timezone

from downloader.models import User, Order, DwzRecord
from downloader.utils import *


if __name__ == '__main__':
    user = User.objects.get(qq_openid='C0207FA138ECDA39D1504427C82C3001')
    print(datetime.date.today().day)
    count = DwzRecord.objects.filter(user=user, create_time__day=datetime.date.today().day).count()
    print(DwzRecord.objects.get(id=6).create_time)
    print(datetime.datetime.now())
    print(count)
    print(timezone.now())










