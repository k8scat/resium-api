# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/3

每天定时凌晨4点检查百度文库cookies是否有效

"""
import requests
from csdnbot.settings.base import CWC_TOKEN

if __name__ == '__main__':
    payload = {
        'cwc_token': CWC_TOKEN
    }
    requests.get('http://localhost:8055/check_wenku_cookies/', params=payload)

