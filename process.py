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

    print(aliyun_oss_sign_url('aaa'))




