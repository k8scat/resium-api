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

from django.core.cache import cache
from django.db.models import Sum


from django.utils import timezone

from downloader.models import User, Order, DwzRecord, CheckInRecord
from downloader.utils import *


if __name__ == '__main__':
    print(timezone.now())
    print(timezone.localtime(timezone.now()).day)






