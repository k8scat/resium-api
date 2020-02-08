# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from .base import *

DEBUG = True

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'csdnbot',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

# 127.0.0.1 本地selenium可下载资源
# 远程 139.199.71.19 selenium只能用于认证
SELENIUM_SERVER = 'http://127.0.0.1:4444/wd/hub'

CSDNBOT_UI = 'http://localhost:3000'

CSDNBOT_API = 'http://localhost:8000'
