# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import json
import logging
from selenium.webdriver.support import expected_conditions as EC
from django.conf import settings
from django.http import HttpResponse
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from downloader.utils import get_driver, add_cookies, ding


def check_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', None)
        if token == settings.ADMIN_TOKEN:
            driver = get_driver()
            try:
                driver.get('https://download.csdn.net/')
                csdn_account = add_cookies(driver, 'csdn')
                driver.get('https://download.csdn.net/my/vip')
                try:
                    valid_count = int(WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[@class='vip_info']/p[1]/span"))
                    ).text)
                    if valid_count <= 0:
                        csdn_account.is_enabled = True
                        csdn_account.save()
                        ding(f'CSDN账号({csdn_account.email})的会员下载数已用完')
                        return HttpResponse('')

                    csdn_account.cookies = json.dumps(driver.get_cookies())
                    csdn_account.save()
                    ding('CSDN cookies 仍有效')
                except TimeoutException:
                    ding('CSDN cookies 已失效，请尽快更新！')
            finally:
                driver.close()
        return HttpResponse('')


def check_baidu_cookies(request):
    """
    检查百度 cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', '')
        if token == settings.ADMIN_TOKEN:
            driver = get_driver()
            try:
                driver.get('https://wenku.baidu.com/')
                baidu_account = add_cookies(driver, 'baidu')
                driver.get('https://wenku.baidu.com/')
                try:
                    username = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[@id='userNameCon']/span[@class='text-dec-under'][1]"))
                    ).text
                    logging.info(username)
                    baidu_account.cookies = json.dumps(driver.get_cookies())
                    baidu_account.save()
                    ding('百度文库 cookies 仍有效')
                except TimeoutException:
                    ding('百度文库 cookies 已失效，请尽快更新！')
            finally:
                driver.close()

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
                docer_account = add_cookies(driver, 'docer')
                driver.get('https://my.docer.com/#!/memberCenter')
                try:
                    vip_id = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@class='pi_my_div_top']/span[@class='grade_text'][1]"))
                    ).text
                    logging.info(vip_id)
                    docer_account.cookies = json.dumps(driver.get_cookies())
                    docer_account.save()
                    ding('稻壳模板 cookies 仍有效')
                except TimeoutException:
                    ding('稻壳模板 cookies 已失效，请尽快更新！')
            finally:
                driver.close()

            return HttpResponse('')
