# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from downloader.models import Resource, User
from downloader.utils import *


if __name__ == '__main__':
    bucket = get_aliyun_oss_bucket()
    # 批量删除3个文件。每次最多删除1000个文件。
    resources = Resource.objects.filter(url__icontains='www.catalina.com.cn').delete()




