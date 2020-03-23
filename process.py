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
    print(check_file_integrity(open('/Users/mac/workspace/pycharm/resium/manual_upload_resource.py', 'rb')))






