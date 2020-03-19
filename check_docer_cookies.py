# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/3

"""
import requests
from csdnbot.settings.base import ADMIN_TOKEN

if __name__ == '__main__':
    payload = {
        'token': ADMIN_TOKEN
    }
    requests.get('https://api.26xf90zp4w.ncucoder.com/check_docer_cookies/', params=payload)
