# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

import json
from selenium import webdriver
from downloader.models import CsdnAccount


if __name__ == '__main__':
    # 扫码登录
    login_url = 'https://passport.csdn.net/login'

    driver = webdriver.Chrome()
    try:
        driver.get(login_url)

        y = input('login ok?')
        if y:
            account = CsdnAccount.objects.get(email='hsowan.v@gmail.com')
            account.driver_cookies = json.dumps(driver.get_cookies())
            account.save()
    finally:
        driver.close()
