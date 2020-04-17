# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/17

"""
import json
import os
from time import sleep

import django
from selenium import webdriver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

from downloader.utils import get_random_ua
import random
import requests
from downloader.models import TaobaoWenkuAccount
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def download(url):
    """
    post http://doc110.com/login.php data {account: "6599362515", password: "9027855"}

    post http://doc110.com/post.php data {docUrl: "https://wenku.baidu.com/view/62c5485ed1d233d4b14e852458fb770bf68a3b76.html?from=search"}
    return {code: 200, downUrl: "url", times: "746", session: "8671203093", msg: "下载成功!", filename: "租房.doc", path: ""}

    get http://doc110.com/get.php return return {code: 200, gold: "746", withdraw: "2", withdraw_accept: true}

    requests似乎没法获取到服务端返回的set-cookie头

    :param url:
    :return:
    """

    driver = webdriver.Chrome()
    try:
        account = random.choice(TaobaoWenkuAccount.objects.filter(is_enabled=True).all())
        driver.get('http://doc110.com/#/login/')
        account_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "(//input[@type='text'])[2]")
            )
        )
        account_input.send_keys(account.account)
        password_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "(//input[@type='password'])[2]")
            )
        )
        password_input.send_keys(account.password)
        login_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "(//a[contains(text(),'立即登陆')])[2]")
            )
        )
        login_button.click()

        url_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='is-accept']/input[@class='input']")
            )
        )
        url_input.send_keys(url)

        download_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='is-accept']/a[@class='btn-lg'][1]")
            )
        )
        download_button.click()

        sleep(100)

    finally:
        driver.close()


if __name__ == '__main__':
    download('https://wenku.baidu.com/view/18263ba4102de2bd9605885e.html?fr=search')
