# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/5/17

"""
import os
from time import sleep

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()

import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import CsdnAccount

if __name__ == '__main__':
    email = '17770040362@163.com'
    account = CsdnAccount.objects.get(email=email, need_sms_validate=True)
    driver = webdriver.Chrome()
    try:
        driver.get('https://csdn.net')
        cookies = json.loads(account.driver_cookies)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)

        driver.get('https://download.csdn.net/download/zdyanshi9/7995337')

        # 下载
        download_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[@class='c_dl_btn download_btn vip_download']"))
        )
        download_button.click()

        # 执行下载
        do_download_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[@class='dl_btn do_download vip_dl_btn']"))
        )
        do_download_button.click()

        # 获取验证码
        get_validate_code_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@id='validate-code']"))
        )
        get_validate_code_button.click()

        # 验证码输入框
        validate_code_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='validate-input']"))
        )
        validate_code_input.send_keys('212121')

        validate_confirm_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@id='sms-confirm']"))
        )
        # validate_confirm_button.click()

        sleep(1000)

    finally:
        driver.close()

