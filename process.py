# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()

from django.conf import settings
import requests


def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    data = {
        'app_id': settings.FEISHU_APP_ID,
        'app_secret': settings.FEISHU_APP_SECRET
    }
    with requests.post(url, json=data) as r:
        if r.status_code == requests.codes.ok:
            res_data = r.json()
            if res_data.get('code', -1) == 0:
                return res_data.get('tenant_access_token', '')
            else:
                return None
        else:
            return None


if __name__ == '__main__':
    print(get_access_token())




