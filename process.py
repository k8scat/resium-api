# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""
import os
import django
from django.core.cache import cache
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()
from django.utils import timezone

from downloader.models import User, Order, DwzRecord, CheckInRecord
from downloader.utils import *


if __name__ == '__main__':
    cache.set('key', 'value')
    print(cache.get('key'))
    cache.delete('key')
    print(cache.get('key'))









