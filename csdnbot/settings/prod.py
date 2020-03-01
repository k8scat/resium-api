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

# 随机标签个数
SAMPLE_TAG_COUNT = 50

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://139.199.71.19:7393/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": "O@RN5#g0.n^o<lU%$CAaw!MDY_P;2txz|]X}4sSdEc(p+3/bZ-",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "retry_on_timeout": True}
        }
    }
}

RATELIMIT_BLOCK = True
