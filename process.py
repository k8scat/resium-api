# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()

from downloader.models import DocerPreviewImage
from downloader.utils import *
from django.core.cache import cache


if __name__ == '__main__':
    cache.set('phone', '17770040362', timeout=10)
    print(cache.get('phone'))
    cache.delete('phone')
    print(cache.get('phone'))







