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

from downloader.models import User, Order
from downloader.utils import *


if __name__ == '__main__':
    Order.objects.filter(has_paid=False).update(is_deleted=True)










