import logging
import sys

from resium.settings.base import *

DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "1234abcd"

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "resium",
        "USER": "resium",
        "PASSWORD": "resium",
        "HOST": "127.0.0.1",
        "PORT": "3306",
        "TIME_ZONE": TIME_ZONE,
    }
}

# 127.0.0.1 本地selenium可下载资源
SELENIUM_SERVER = "http://127.0.0.1:4444/wd/hub"

FRONTEND_URL = "http://localhost:3000"

API_BASE_URL = "http://localhost:8000"

# 随机标签个数
SAMPLE_TAG_COUNT = 3

REDIS_HOST = "127.0.0.1"
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

RATELIMIT_BLOCK = False

COOKIE_DOMAIN = "localhost"

# 下载文件的存放目录
DOWNLOAD_DIR = os.path.join(
    os.path.dirname(BASE_DIR), "resium-scripts/volumes/selenium/download"
)
if not os.path.isdir(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

NGINX_DOWNLOAD_URL = f"file://{DOWNLOAD_DIR}"

DOWNHUB_SERVER = "http://127.0.0.1:8080"
DOWNHUB_TOKEN = "1234abcd"

# 用于授权更新版本信息，调用 /update_version 接口
VERSION_TOKEN = "1234abcd"

# 用于登录学校VPN
ZHIWANG_VPN_USERNAME = ""
ZHIWANG_VPN_PASSWORD = ""

# http://www.fateadm.com/user_home.php
PD_ID = ""
PD_KEY = ""

JWT_SECRET = ""

ALIYUN_ACCESS_KEY_ID = ""
ALIYUN_ACCESS_KEY_SECRET = ""
ALIYUN_OSS_END_POINT = ""
ALIYUN_OSS_BUCKET_NAME = ""
ALIYUN_OSS_DOMAIN = ""

DINGTALK_ACCESS_TOKEN = ""
DINGTALK_SECRET = ""

# 管理员凭证
ADMIN_TOKEN = ""

EMAIL_HOST = ""
EMAIL_PORT = 465
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = ""
ADMIN_EMAIL = ""

# 微信小程序
WX_MP_APP_ID = ""
WX_MP_APP_SECRET = ""

# 微信支付
WX_PAY_MP_APP_ID = ""
WX_PAY_MP_APP_SECRET = ""

WX_PAY_SUB_APP_ID = WX_PAY_MP_APP_ID  # 当前调起支付的小程序APPID
WX_PAY_MCH_ID = ""
WX_PAY_API_KEY = ""  # 商户 key
WX_PAY_MCH_CERT = os.path.join(
    os.path.join(BASE_DIR, "wx_pay_cert"), "apiclient_cert.pem"
)
WX_PAY_MCH_KEY = os.path.join(
    os.path.join(BASE_DIR, "wx_pay_cert"), "apiclient_key.pem"
)

ADMIN_UID = []

# https://open.feishu.cn/document/uQjL04CN/uYTMuYTMuYTM
FEISHU_APP_ID = ""
FEISHU_APP_SECRET = ""
FEISHU_APP_VERIFICATION_TOKEN = ""
FEISHU_APP_ENCRYPT_KEY = ""
FEISHU_USER_ID = ""
FEISHU_TOKEN_INTERVAL = 3600
FEISHU_TOKEN_CACHE_KEY = "feishu:token"

RSA_PRIVKEY_FILE = os.path.join(BASE_DIR, "private-key.pem")
RSA_PUBKEY_FILE = os.path.join(BASE_DIR, "public-key.pem")
