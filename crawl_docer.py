# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/29

爬取docer资源

"""
import json
import os
import re
import time

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
from django.conf import settings

from downloader.utils import parse_cookies, get_driver, check_download


def login():
    pass


def download(download_url, unique_folder):
    docer_home = 'https://www.docer.com/'

    driver = get_driver(os.path.join('docer', unique_folder))

    try:
        # 先请求，再添加cookies
        # selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
        driver.get(docer_home)
        # 从文件中获取到cookies
        with open(cookies_file, 'r', encoding='utf-8') as f:
            cookies = json.loads(f.read())
        for c in cookies:
            driver.add_cookies({'name': c['name'], 'value': c['value'], 'path': c['path'], 'domain': c['domain'],
                               'secure': c['secure']})
        driver.get(download_url)
        time.sleep(1)
        # 获取word名称
        word_name = driver.find_element_by_xpath(
            "/html/body/div[@id='__nuxt']/div[@id='__layout']/div[@id='App']/div[@class='g-router-regular']/div[2]/div[@class='preview g-clearfloat']/div[@class='preview__info']/h1[@class='preview__title']").text
        # 只要简历模板
        # if word_name.find('简历') == -1:
        #     return

        # 获取word编号
        pattern = re.compile(r'\d+')
        word_id = pattern.findall(driver.find_element_by_xpath(
            "/html/body/div[@id='__nuxt']/div[@id='__layout']/div[@id='App']/div[@class='g-router-regular']/div[2]/div[@class='preview g-clearfloat']/div[@class='preview__info']/ul[@class='preview__detail g-clearfloat']/li[@class='preview__detail-item'][3]").text)[
            0]

        # 是否是VIP模板
        is_vip = driver.find_element_by_xpath(
            "/html/body/div[@id='__nuxt']/div[@id='__layout']/div[@id='App']/div[@class='g-router-regular']/div[2]/div[@class='preview g-clearfloat']/div[@class='preview__info']/ul[@class='preview__detail g-clearfloat']/li[@class='preview__detail-item'][4]").text.find(
            'VIP') != -1
        # 只爬取VIP模板
        if not is_vip:
            return

        download_button = WebDriverWait(driver, 60).until(EC.presence_of_element_located(
            (By.XPATH,
             "/html/body/div[@id='__nuxt']/div[@id='__layout']/div[@id='App']/div[@class='g-router-regular']/div[2]/div[@class='preview g-clearfloat']/div[@class='preview__info']/div[@class='preview__btns g-clearfloat']/span[2]"))
        )
        download_button.click()

        check_download()




    finally:
        driver.quit()


if __name__ == '__main__':
    pass
