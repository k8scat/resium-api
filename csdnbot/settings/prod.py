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
        'PASSWORD': 'Holdon@7868',
        'HOST': '49.235.161.70',  # 49.235.161.70
        'PORT': '3306',
    }
}

SELENIUM_SERVER = 'http://selenium:4444/wd/hub'

CSDNBOT_UI = 'https://csdnbot.com'

CSDNBOT_API = 'https://api.csdnbot.ncucoder.com'
