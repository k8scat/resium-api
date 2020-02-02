# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/29

每天凌晨3点定时刷新cookies

"""
import requests
from csdnbot.settings.base import RC_TOKEN


if __name__ == '__main__':
    payload = {
        'rc_token': RC_TOKEN
    }
    requests.get('http://localhost:8055/refresh_cookies/', params=payload)

