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

from django.core.cache import cache
from django.db.models import Sum


from django.utils import timezone

from downloader.models import User, Order, CheckInRecord
from downloader.utils import *


if __name__ == '__main__':
    qq_send_private_msg(1583096683, 'hello')





