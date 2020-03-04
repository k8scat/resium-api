# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""

import os
from time import sleep

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()

from downloader.models import *
from downloader.utils import *


if __name__ == '__main__':
    from django.core.cache import cache
    cache.set('hello', 'world', timeout=1)
    sleep(0.5)
    print(cache.get('hello'))







