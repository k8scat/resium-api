# -*- coding: utf-8 -*-
"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from resium.settings.base import *

DEBUG = False

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "resium",
        "USER": "root",
        "PASSWORD": "Holdon@7868",
        "HOST": "resium-db",  # 116.63.142.111
        "PORT": "3306",
        "TIME_ZONE": TIME_ZONE,
    }
}

SELENIUM_SERVER = "http://resium-selenium:4444/wd/hub"

FRONTEND_URL = "https://resium.cn"
API_BASE_URL = "https://api.resium.ncucoder.com"

WX_PAY_NOTIFY_URL = API_BASE_URL + "/mp_pay_notify/"
ALIPAY_APP_NOTIFY_URL = API_BASE_URL + "/alipay_notify/"

# 随机标签个数
SAMPLE_TAG_COUNT = 50

REDIS_HOST = "resium-redis"
REDIS_PORT = 6379
REDIS_DB = 1
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,
                "retry_on_timeout": True,
            },
        },
    }
}

RATELIMIT_BLOCK = True

sentry_sdk.init(
    dsn="https://ca79fc2104324d859b1d5f8aee301567@sentry.io/5185473",
    integrations=[DjangoIntegration()],
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)

COOKIE_DOMAIN = "resium.cn"

# 下载文件的存放目录
DOWNLOAD_DIR = os.path.join(BASE_DIR, "download")
if not os.path.isdir(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
NGINX_DOWNLOAD_URL = "https://file.resium.ncucoder.com"

DOWNHUB_SERVER = "http://resium-downhub:8080"
DOWNHUB_TOKEN = "NhGBSTHWuFtjlLUD6Q37KIc2svmgoXrOA4fYzE8b"

# 用于授权更新版本信息，调用 /update_version 接口
VERSION_TOKEN = "jZpsduVlmCPHv0Y1U5Sb3hEJkgzcKTXifFItarO2Ro"
