# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/3

"""
import requests
from resium.settings.base import ADMIN_TOKEN

if __name__ == '__main__':
    payload = {
        'token': ADMIN_TOKEN
    }
    requests.post('http://localhost:8000/check_docer_cookies/', data=payload)
