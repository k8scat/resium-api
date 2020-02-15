# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from .base import *

DEBUG = False

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'csdnbot',
        'USER': 'root',
        'PASSWORD': 'Holdon@7868',
        'HOST': '139.199.71.19',
        'PORT': '3306',
    }
}

SELENIUM_SERVER = 'http://selenium:4444/wd/hub'

CSDNBOT_UI = 'https://resium.ncucoder.com'

CSDNBOT_API = 'https://api.csdnbot.ncucoder.com'
