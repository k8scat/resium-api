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

    print(re.match(r'^callback\( {"client_id":".+","openid":".+"} \);$',
                   'callback( {"client_id":"101864025","openid":"C0207FA138ECDA39D1504427C82C3001"} );'))






