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
    filepath = '/Users/mac/workspace/pycharm/resium/download/ac4f0d96-6cfd-11ea-873b-a0999b0715d5/Saki-the-open-window-分析.ppt'
    print(zip_file(filepath))






