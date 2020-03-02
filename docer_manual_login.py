# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/1

"""
import json
import os

from selenium import webdriver

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()
from downloader.models import DocerAccount


if __name__ == '__main__':
    docer_account = DocerAccount.objects.get(email='17770040362@163.com')
    driver = webdriver.Chrome()
    try:
        driver.get('https://www.docer.com/')

        if input('是否登录成功: ') == 'y':
            docer_account.cookies = json.dumps(driver.get_cookies())
            docer_account.save()

    finally:
        driver.close()
