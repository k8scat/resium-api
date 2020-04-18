"""
Django settings for resium project.

Generated by 'django-admin startproject' using Django 3.0.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ')_du2k%k)d+hmofh_c071maigkuppa6jszwbm%3_47uw3xu%oc'

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'downloader.apps.DownloaderConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'resium.middleware.CorsMiddleware'
]

ROOT_URLCONF = 'resium.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'resium.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_URL = '/static/'
# 用于 python manage.py collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

EMAIL_HOST = 'smtp.exmail.qq.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'admin@resium.cn'
EMAIL_HOST_PASSWORD = 'QLVNHSDDDAAQCYWj'
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = f'源自下载 <{EMAIL_HOST_USER}>'

# https://github.com/adamchainz/django-cors-headers
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with'
]
CORS_ORIGIN_ALLOW_ALL = True
# 暴露给前端的header
CORS_EXPOSE_HEADERS = [
    'Content-Disposition'
]

CSDN_COOKIES_FILE = os.path.join(BASE_DIR, 'csdn_cookies.json')
BAIDU_COOKIES_FILE = os.path.join(BASE_DIR, 'baidu_cookies.json')

REQUEST_TOKEN_HEADER = 'Authorization'
REQUEST_TOKEN_PREFIX = 'Bearer '

# 下载文件的存放目录
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'download')
# 上传资源的存放目录
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload')

JWT_SECRET = 'yJzb21lIjoicGF5bG9hZCJ'

ALIPAY_APP_ID = '2021001106627048'
ALIPAY_APP_PRIVATE_KEY_FILE = os.path.join(BASE_DIR, 'alipay_app_private_key.pem')
ALIPAY_PUBLIC_KEY_FILE = os.path.join(BASE_DIR, 'alipay_public_key.pem')
ALIPAY_WEB_BASE_URL = 'https://openapi.alipay.com/gateway.do?'

DINGTALK_ACCESS_TOKEN = 'c10fd5991b46481142648156bee6dbf48981277a7c6bc803b168f14f047673cc'
DINGTALK_SECRET = 'SEC0fde189fef95beb0d23a5469cccfc74c9d0da70b104cdd256cafa2a31fb7b723'

ALIYUN_ACCESS_KEY_ID = 'LTAIcgObSb2Q8y1y'
ALIYUN_ACCESS_KEY_SECRET = 'JpncsRuQgykFJqN79EDwX23vIhKtOW'
ALIYUN_OSS_END_POINT = 'http://oss-cn-hangzhou.aliyuncs.com'
ALIYUN_OSS_BUCKET_NAME = 'ncucoder'
ALIYUN_OSS_USER_DOMAIN = 'http://cdn.ncucoder.com/'
ALIYUN_OSS_DOMAIN = 'http://ncucoder.oss-cn-hangzhou.aliyuncs.com'

TAG_SEP = '!sep!'

# 管理员凭证
ADMIN_TOKEN = 'csSM0Aw4NrvpZfxDEtbB3mPCWVUK52OnQik9djuLz1Ih8aToGJ'

SWAGGER_SETTINGS = {
   'SECURITY_DEFINITIONS': {
      'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
      }
   }
}

WX_APP_SECRET = '2fe6a20c1ea55e57952c7f7baa721acb'
WX_TOKEN = '6zOpjsMV15xWihocay4grCRPY82EQS7m'
WX_APP_ID = 'wx687355ca576bb3d2'
WX_ENCODING_AES_KEY = 'L32ggf9lyXAC7Noc37I3OrPLPW8HqzS6rgb9hC4ImNW'

# 资源积分
WENKU_VIP_FREE_DOC_POINT = 1
WENKU_SHARE_DOC_POINT = 1
WENKU_SPECIAL_DOC_POINT = 20
CSDN_POINT = 5
DOCER_POINT = 1
OSS_RESOURCE_POINT = 1
ZHIWANG_POINT = 10
ARTICLE_POINT = 1
QIANTU_POINT = 1

MY_CSDN_ACCOUNT = '17770040362@163.com'

# http://www.fateadm.com/user_home.php
PD_ID = '120959'
PD_KEY = 'pxnfBZw6RfkAXOh5uOygeHoCy52e6wRp'
SCREENSHOT_IMAGE = os.path.join(BASE_DIR, 'screenshot.png')
CODE_IMAGE = os.path.join(BASE_DIR, 'code.png')

# 用于登录学校VPN
NCU_VPN_USERNAME = '8000116092'
NCU_VPN_PASSWORD = 'holdon7868'

# 资源下载间隔
DOWNLOAD_INTERVAL = 60
COOLQ_DOWNLOAD_INTERVAL = 180

# https://note.qidong.name/2018/11/django-logging/
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR + '/resium.log',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# 机器人和后端通信的唯一凭证，直接放在post的data中，key是token
BOT_TOKEN = 'w1hLAtyOV3QYq0xaWcrklXzG9KpFsnuD'

PATTERN_CSDN = r'^(http(s)?://download\.csdn\.net/download/).+$'
PATTERN_WENKU = r'^(http(s)?://wenku\.baidu\.com/view/).+$'
PATTERN_DOCER = r'^(http(s)?://www\.docer\.com/(webmall/)?preview/).+$'
PATTERN_ZHIWANG = r'^(http(s)?://kns(8)?\.cnki\.net/KCMS/detail/).+$'
PATTERN_QIANTU = r'^(http(s)?://www\.58pic\.com/newpic/)\d+(\.html)$'

COOLQ_API = 'http://49.235.161.70:5700'
COOLQ_AUTH_HEADERS = {
    'Authorization': 'Bearer eyJzdWIiOiJoc293YW4ubWVryFUdFEEzz77SBjC3GxleM9uSP'
}

wenku_accounts = [
    {
        'account': '6599362515',
        'password': '9027855'
    }
]

BAIDU_DWZ_TOKEN = '599899227931471a4e48c50e92495880'

# https://connect.qq.com/manage.html#/appinfo/web/101864025
QQ_CLIENT_ID = '101864025'
QQ_CLIENT_SECRET = 'be9503e910cd150287453f0a0bcce9bc'
QQ_REDIRECT_URI = 'https://api.resium.cn/oauth/qq'

# https://github.com/settings/applications/1269223
GITHUB_CLIENT_ID = 'd91f5182093a379e63b7'
GITHUB_CLIENT_SECRET = '4ada14d10f0af0c77e7ea50e34f73fe29a26ce2a'

# https://gitee.com/api/v5/oauth_doc#/
GITEE_CLIENT_ID = '77b39c9e80ef1a308c1f684c954b20f6b0820f84a0624490e9741c44ba8e30f4'
GITEE_CLIENT_SECRET = 'e4f814cff8d0a9684a9daac4b1c0c5e8d7f8775f9706cda1b5ecd3ec03006903'
GITEE_REDIRECT_URI = 'https://api.resium.cn/oauth/gitee/'

BAIDU_CLIENT_ID = 'PYvdAfLebKVt6b9fT8QbpquE'
BAIDU_CLIENT_SECRET = 'v9lVuSG5OrayzXOG1jKZYCcLPC90WjGB'
BAIDU_REDIRECT_URI = 'https://api.resium.cn/oauth/baidu/'

JWT_COOKIE_KEY = 'token'
