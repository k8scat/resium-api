# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()

from downloader.utils import *
from django.core.cache import cache


if __name__ == '__main__':
    cache.set('key1', 1, timeout=10)
    print(cache.get('key'))
    print(cache.get('key1'))







