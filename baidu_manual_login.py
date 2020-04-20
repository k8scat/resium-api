# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/3

获取并保存百度的cookies

"""
import json
import os

from selenium import webdriver
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()
from downloader.models import BaiduAccount


if __name__ == '__main__':
    # 测试登陆
    baidu_account = BaiduAccount.objects.get(email='17770040362@163.com')
    wenku_home = 'https://wenku.baidu.com/'

    driver = webdriver.Chrome()
    try:
        driver.get(wenku_home)

        if input('是否登录成功: ') == 'y':
            baidu_account.cookies = json.dumps(driver.get_cookies())
            baidu_account.save()

    finally:
        driver.close()
