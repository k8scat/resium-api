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
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ")_du2k%k)d+hmofh_c071maigkuppa6jszwbm%3_47uw3xu%oc"

ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "downloader.apps.DownloaderConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # 'django.middleware.csrf.CsrfViewMiddleware',
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "resium.middleware.CorsMiddleware",
]

ROOT_URLCONF = "resium.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "resium.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "zh-hans"

TIME_ZONE = "Asia/Shanghai"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_URL = "/static/"
# 用于 python manage.py collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, "static")

EMAIL_HOST = "smtp.exmail.qq.com"
EMAIL_PORT = 465
EMAIL_HOST_USER = "support@huayin.io"
EMAIL_HOST_PASSWORD = "dg5xmNfHKm9QuChV"
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = f"华隐软件 <{EMAIL_HOST_USER}>"
ADMIN_EMAIL = "1583096683@qq.com"

# https://github.com/adamchainz/django-cors-headers
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_ORIGIN_ALLOW_ALL = True
# 暴露给前端的header
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

CSDN_COOKIES_FILE = os.path.join(BASE_DIR, "csdn_cookies.json")
BAIDU_COOKIES_FILE = os.path.join(BASE_DIR, "baidu_cookies.json")

REQUEST_TOKEN_HEADER = "Authorization"
REQUEST_TOKEN_PREFIX = "Bearer "

# 上传资源的存放目录
UPLOAD_DIR = os.path.join(BASE_DIR, "upload")
if not os.path.isdir(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

JWT_SECRET = "yJzb21lIjoicGF5bG9hZCJ"

ALIPAY_APP_ID = "2021001164668010"
ALIPAY_APP_PRIVATE_KEY_FILE = os.path.join(BASE_DIR, "alipay_app_private_key.pem")
ALIPAY_PUBLIC_KEY_FILE = os.path.join(BASE_DIR, "alipay_public_key.pem")
ALIPAY_WEB_BASE_URL = "https://openapi.alipay.com/gateway.do?"

ALIYUN_ACCESS_KEY_ID = "LTAI4GKsvHSHHuc6uffSsBUE"
ALIYUN_ACCESS_KEY_SECRET = "IfXJZGPtGUNfSPHGMBEd9c2HFGTyux"
ALIYUN_OSS_END_POINT = "http://oss-cn-hangzhou.aliyuncs.com"
ALIYUN_OSS_BUCKET_NAME = "ncucoder"
ALIYUN_OSS_USER_DOMAIN = "http://cdn.ncucoder.com/"
ALIYUN_OSS_DOMAIN = "http://ncucoder.oss-cn-hangzhou.aliyuncs.com"

DINGTALK_ACCESS_TOKEN = (
    "c10fd5991b46481142648156bee6dbf48981277a7c6bc803b168f14f047673cc"
)
DINGTALK_SECRET = "SEC0fde189fef95beb0d23a5469cccfc74c9d0da70b104cdd256cafa2a31fb7b723"

# 管理员凭证
ADMIN_TOKEN = "csSM0Aw4NrvpZfxDEtbB3mPCWVUK52OnQik9djuLz1Ih8aToGJ"

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    }
}

# 微信公众号
WX_APP_SECRET = "2fe6a20c1ea55e57952c7f7baa721acb"
WX_TOKEN = "6zOpjsMV15xWihocay4grCRPY82EQS7m"
WX_APP_ID = "wx687355ca576bb3d2"
WX_ENCODING_AES_KEY = "L32ggf9lyXAC7Noc37I3OrPLPW8HqzS6rgb9hC4ImNW"

# 微信小程序
WX_MP_APP_ID = "wxbdad878a32644dca"
WX_MP_APP_SECRET = "91b3ad866563bf2c4248689e4edbdad8"

# 微信支付
WX_PAY_MP_APP_ID = "wx909d8ff5894ec49b"
WX_PAY_MP_APP_SECRET = "fd9533054324c786d7eb7f5dcaf4779e"

# 资源积分
WENKU_VIP_FREE_DOC_POINT = 10
WENKU_SHARE_DOC_POINT = 20
WENKU_SPECIAL_DOC_POINT = 20
CSDN_POINT = 10
DOCER_POINT = 10
OSS_RESOURCE_POINT = 10
ZHIWANG_POINT = 10
ARTICLE_POINT = 1
QIANTU_POINT = 10
DOC_CONVERT_POINT = 10
PUDN_POINT = 10
ITEYE_POINT = CSDN_POINT
MBZJ_POINT = 10

# http://www.fateadm.com/user_home.php
# hsowan.me@gmail.com
PD_ID = "120959"
PD_KEY = "pxnfBZw6RfkAXOh5uOygeHoCy52e6wRp"

ZHIWANG_SCREENSHOT_IMAGE = os.path.join(BASE_DIR, "zhiwang_screenshot.png")
ZHIWANG_CODE_IMAGE = os.path.join(BASE_DIR, "zhiwang_code.png")
WENKU_SCREENSHOT_IMAGE = os.path.join(BASE_DIR, "wenku_screenshot.png")
WENKU_CODE_IMAGE = os.path.join(BASE_DIR, "wenku_code.png")

# 用于登录学校VPN
NCU_VPN_USERNAME = "8000116092"
NCU_VPN_PASSWORD = "holdon7868"

# 资源下载间隔, 单位s
DOWNLOAD_INTERVAL = 60
# 邮箱绑定链接的有效时间, 单位s
EMAIL_CODE_EXPIRES = 600

# https://note.qidong.name/2018/11/django-logging/
LOG_FOLDER = os.path.join(BASE_DIR, "logs")
if not os.path.isdir(LOG_FOLDER):
    os.makedirs(LOG_FOLDER, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(
                LOG_FOLDER,
                time.strftime("%Y-%m-%d", time.localtime(time.time())),
            ),
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "django": {
            "handlers": ["console", "file"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

PATTERN_CSDN = r"^(http(s)?://download\.csdn\.net/(download|detail)/).+/\d+$"
PATTERN_WENKU = r"^(http(s)?://w(en)?k(u)?\.baidu\.com/view/).+$"
PATTERN_DOCER = r"^(http(s)?://www\.docer\.com/(webmall/)?preview/).+$"
PATTERN_ZHIWANG = r"^(http(s)?://kns(8)?\.cnki\.net/KCMS/detail/).+$"
PATTERN_QIANTU = r"^(http(s)?://www\.58pic\.com/newpic/)\d+(\.html)$"
PATTERN_PUDN = r"^http(s)?://www\.pudn\.com/Download/item/id/\d+\.html$"
PATTERN_ITEYE = r"^http(s)?://www\.iteye\.com/resource/.+-\d+$"
PATTERN_MBZJ = r"^(http(s)?://www\.cssmoban\.com/(cssthemes|wpthemes)/\d+\.shtml).*$"

BAIDU_DWZ_TOKEN = "599899227931471a4e48c50e92495880"

# https://connect.qq.com/manage.html#/appinfo/web/101864025
QQ_CLIENT_ID = "101864025"
QQ_CLIENT_SECRET = "be9503e910cd150287453f0a0bcce9bc"
QQ_REDIRECT_URI = "https://api.resium.ncucoder.com/oauth/qq"

# OAuth重定向时的cookie键
JWT_COOKIE_KEY = "token"

# 二维码有效期为5分钟
QR_CODE_EXPIRE = 300

WX_PAY_APP_ID = WX_APP_ID  # 微信公众号 appid，使用未认证的appid
WX_PAY_SUB_APP_ID = WX_PAY_MP_APP_ID  # 当前调起支付的小程序APPID
WX_PAY_MCH_ID = "1593040541"
WX_PAY_API_KEY = "N4tcdilXJOLEQkwb9h1KIxYn6BTDvRm7"  # 商户 key
WX_PAY_MCH_CERT = os.path.join(
    os.path.join(BASE_DIR, "wx_pay_cert"), "apiclient_cert.pem"
)
WX_PAY_MCH_KEY = os.path.join(
    os.path.join(BASE_DIR, "wx_pay_cert"), "apiclient_key.pem"
)

CSDN_DOWNLOADING_KEY = "csdn_downloading"
CSDN_DOWNLOADING_MAX_TIME = 300

QINIU_ACCESS_KEY = "Adx9fTjienPcF8duV2nQQxZUUt33P4aHPAMbO8a2"
QINIU_SECRET_KEY = "orLcntGa69dqdrgo8HCsnjR_YjGgpSchVsIV3v7g"
QINIU_OPEN_BUCKET = "ncucoder"
QINIU_OPEN_DOMAIN = "cdn.qiniu.ncucoder.com"

ADMIN_UID = ["666666"]

# https://open.feishu.cn/document/uQjL04CN/uYTMuYTMuYTM
FEISHU_APP_ID = "cli_9fa469f57e2c900e"
FEISHU_APP_SECRET = "zmmz9FT8Hro4yFOK8TfMIdXzvfChRur3"
FEISHU_APP_VERIFICATION_TOKEN = "lGNcI2MU2r645g7uH0xJjdyd2jc3npJb"
FEISHU_APP_ENCRYPT_KEY = "n5z0Rp2yeLMOdwwWpkgqXfjtiIuUneMf"
FEISHU_USER_ID = "819d28c8"
FEISHU_TOKEN_INTERVAL = 3600
FEISHU_TOKEN_CACHE_KEY = "feishu:token"

ADMIN_CSDN_ACCOUNTS = ["65634914", "79337844"]

RSA_PRIVKEY_FILE = os.path.join(BASE_DIR, "private-key.pem")
RSA_PUBKEY_FILE = os.path.join(BASE_DIR, "public-key.pem")

FILE_TYPES = {
    "1": "DOC",
    "2": "XLS",
    "3": "PPT",
    "4": "DOCX",
    "5": "XLSX",
    "6": "PPTX",
    "7": "PDF",
    "8": "TXT",
    "9": "WPS",
    "12": "VSD",
    "13": "RTF",
    "15": "PPS",
    "19": "DWG",
}

TAG_SEP = "!sep!"
