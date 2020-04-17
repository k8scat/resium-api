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
        'NAME': 'resium',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

# 127.0.0.1 本地selenium可下载资源
# 远程 139.199.71.19 selenium只能用于认证
SELENIUM_SERVER = 'http://127.0.0.1:4444/wd/hub'

RESIUM_UI = 'http://localhost:3000'

RESIUM_API = 'http://localhost:8000'

# 随机标签个数
SAMPLE_TAG_COUNT = 3

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": "O@RN5#g0.n^o<lU%$CAaw!MDY_P;2txz|]X}4sSdEc(p+3/bZ-",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "retry_on_timeout": True}
        }
    }
}

RATELIMIT_BLOCK = False

from . import prod
ALIPAY_APP_NOTIFY_URL = prod.RESIUM_API + '/alipay_notify/'

COOKIE_DOMAIN = 'localhost'

DEV_UID = '6feb03847f9311eab478a0999b0715d5.1587008180.2814999'
