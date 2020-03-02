# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import json
import logging
from threading import Thread
from selenium.webdriver.support import expected_conditions as EC
import requests
from django.conf import settings
from django.http import HttpResponse
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import DocerAccount
from downloader.utils import csdn_auto_login, baidu_auto_login, get_driver, add_cookies, ding


def refresh_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', None)
        if token == settings.ADMIN_TOKEN:
            t = Thread(target=csdn_auto_login)
            t.start()
        return HttpResponse('')


def refresh_baidu_cookies(request):
    """
    更新百度 cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', '')
        if token == settings.ADMIN_TOKEN:
            t = Thread(target=baidu_auto_login)
            t.start()
        return HttpResponse('')


def check_docer_cookies(request):
    """
    检查稻壳模板 cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', '')
        if token == settings.ADMIN_TOKEN:
            driver = get_driver()
            try:
                driver.get('https://www.docer.com/')
                add_cookies(driver, 'docer')
                driver.get('https://my.docer.com/#!/memberCenter')
                try:
                    vip_id = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@class='pi_my_div_top']/span[@class='grade_text'][1]"))
                    ).text
                    logging.info(vip_id)
                    ding('稻壳模板 cookies 仍有效')
                except TimeoutException:
                    ding('稻壳模板 cookies 已失效，请尽快更新！')
            finally:
                driver.close()

            return HttpResponse('')
