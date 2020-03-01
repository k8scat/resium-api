# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/1

"""
import json
import os

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()
from downloader.models import DocerAccount
from django.conf import settings


def docer_manual_login():
    docer_home = 'https://www.docer.com/'

    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps)
    try:
        driver.get(docer_home)

        if input('是否登录成功(默认登陆成功): ') == 'n':
            return []

        return driver.get_cookies()

    finally:
        driver.close()


if __name__ == '__main__':
    docer_account = DocerAccount.objects.get(email='17770040362@163.com')
    cookies = docer_manual_login()
    if len(cookies):
        docer_account.cookies = json.dumps(cookies)
        docer_account.save()
        print('ok')
    else:
        print('error')
