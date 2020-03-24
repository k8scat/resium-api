# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/29

每天凌晨3点定时刷新cookies

"""
import requests
from resium.settings.base import ADMIN_TOKEN


if __name__ == '__main__':
    payload = {
        'token': ADMIN_TOKEN
    }
    requests.post('http://localhost:8000/check_csdn_cookies/', data=payload)

