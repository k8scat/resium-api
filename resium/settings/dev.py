# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from .base import *
import sys
import logging

DEBUG = True

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'resium',
        'USER': 'resium',
        'PASSWORD': 'resium',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'TIME_ZONE': TIME_ZONE
    }
}

# 127.0.0.1 本地selenium可下载资源
# 远程 139.199.71.19 selenium只能用于认证
SELENIUM_SERVER = 'http://127.0.0.1:4444/wd/hub'

FRONTEND_URL = 'http://localhost:3000'

API_BASE_URL = 'http://localhost:8000'

# 随机标签个数
SAMPLE_TAG_COUNT = 3

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 1
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "retry_on_timeout": True}
        }
    }
}

RATELIMIT_BLOCK = False

COOKIE_DOMAIN = 'localhost'

# 下载文件的存放目录

DOWNLOAD_DIR = os.path.join(os.path.dirname(
    BASE_DIR), 'resium-scripts/volumes/selenium/download')
if not os.path.isdir(DOWNLOAD_DIR):
    logging.error(f'Invalid setting DOWNLOAD_DIR: {DOWNLOAD_DIR}')
    sys.exit(1)
NGINX_DOWNLOAD_URL = f'file://{DOWNLOAD_DIR}'

DOWNHUB_SERVER = 'http://127.0.0.1:8080'
DOWNHUB_TOKEN = 'NhGBSTHWuFtjlLUD6Q37KIc2svmgoXrOA4fYzE8b'

# 用于授权更新版本信息，调用 /update_version 接口
VERSION_TOKEN = 'Oh7YEamixSzLlu6fK3tdDIcVFRyQ8rGb'
