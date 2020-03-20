# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/29

每天凌晨3点定时刷新cookies

"""
import requests
from csdnbot.settings.base import ADMIN_TOKEN


if __name__ == '__main__':
    payload = {
        'token': ADMIN_TOKEN
    }
    requests.post('https://api.26xf90zp4w.ncucoder.com/check_csdn_cookies/', data=payload)

