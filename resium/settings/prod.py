# -*- coding: utf-8 -*-
"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = False

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'resium',
        'USER': 'root',
        'PASSWORD': 'Holdon@7868',
        'HOST': 'resium-db',
        'PORT': '3306',
    }
}

SELENIUM_SERVER = 'http://resium-selenium:4444/wd/hub'

FRONTEND_URL = 'https://resium.cn'
API_BASE_URL = 'https://api.resium.ncucoder.com'

WX_PAY_NOTIFY_URL = API_BASE_URL + '/mp_pay_notify/'
ALIPAY_APP_NOTIFY_URL = API_BASE_URL + '/alipay_notify/'

# 随机标签个数
SAMPLE_TAG_COUNT = 50

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://resium-redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "retry_on_timeout": True}
        }
    }
}

RATELIMIT_BLOCK = True

sentry_sdk.init(
    dsn="https://ca79fc2104324d859b1d5f8aee301567@sentry.io/5185473",
    integrations=[DjangoIntegration()],

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)

COOKIE_DOMAIN = 'resium.cn'

NGINX_DOWNLOAD_URL = 'https://file.resium.ncucoder.com'
