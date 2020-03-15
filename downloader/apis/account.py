# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import json
import logging

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.support import expected_conditions as EC
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import DocerAccount, CsdnAccount, BaiduAccount
from downloader.utils import get_driver, ding


def check_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', None)
        if token == settings.ADMIN_TOKEN:
            csdn_accounts = CsdnAccount.objects.all()
            for csdn_account in csdn_accounts:
                headers = {
                    'cookie': csdn_account.cookies
                }
                with requests.get('https://download.csdn.net/my/vip', headers=headers) as r:
                    soup = BeautifulSoup(r.text, 'lxml')
                    el = soup.select('div.vip_info p:nth-of-type(1) span')
                    if el:
                        ding(f'CSDN会员账号剩余下载个数: {el[0].text}')
                    else:
                        ding('CSDN会员账号的cookies已失效，请及时更新')

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

                # 添加cookies
                try:
                    baidu_account = BaiduAccount.objects.get(is_enabled=True)
                except BaiduAccount.DoesNotExist:
                    ding('没有可用的百度文库会员账号')
                    return JsonResponse(dict(code=500, msg='下载失败'))
                cookies = json.loads(baidu_account.cookies)
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    driver.add_cookie(cookie)

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
            try:
                docer_account = DocerAccount.objects.get(is_enabled=True)
                headers = {
                    'cookie': docer_account.cookies
                }
                url = 'https://www.docer.com/proxy-docer/v4.php/api/user/allinfo'
                with requests.get(url, headers=headers) as r:
                    if r.json()['result'] == 'ok':
                        ding('稻壳模板cookies仍有效')
                    else:
                        ding('稻壳模板cookies已失效，请尽快更新')
            except DocerAccount.DoesNotExist:
                ding('没有可以使用的稻壳模板会员账号')

        return HttpResponse('')


def reset_csdn_today_download_count(request):
    """
    重置CSDN账号的今日已下载数
    """

    if request.method == 'GET':
        token = request.GET.get('token', None)
        if token == settings.ADMIN_TOKEN:
            csdn_accounts = CsdnAccount.objects.all()
            for csdn_account in csdn_accounts:
                csdn_account.today_download_count = 0
                csdn_account.save()
        return HttpResponse('')
