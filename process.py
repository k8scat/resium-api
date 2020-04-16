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

from downloader.models import User
from downloader.utils import *


if __name__ == '__main__':
    for user in User.objects.all():
        uid = f"{str(uuid.uuid1()).replace('-', '')}.{str(time.time())}"
        user.uid = uid
        user.save()






