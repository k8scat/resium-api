# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/17

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()
from downloader.utils import aliyun_oss_check_file

if __name__ == '__main__':
    print(aliyun_oss_check_file('f859f5de-5164-11ea-bf8e-a0999b0715d5-MODBUS软件开发实战指南.pdf'))
