# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/29

已不能使用

"""
import json
import os
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()
from downloader.models import BaiduAccount


if __name__ == '__main__':
    # 测试登陆
    baidu_account = BaiduAccount.objects.get(email='17770040362@163.com')

    cloud_login_url = 'https://login.bce.baidu.com/'
    console = 'https://console.bce.baidu.com/'
    wenku_home = 'https://wenku.baidu.com/'
    logout = 'https://passport.baidu.com/?logout&aid=7&u=https%3A//login.bce.baidu.com/'

    # driver = webdriver.Chrome()

    selenium_server = 'http://139.199.71.19:4567/wd/hub'
    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=selenium_server, desired_capabilities=caps)

    try:
        # 先访问百度首页, 否则直接登录百度网盘的话, 百度依旧会需要验证登录
        driver.get(wenku_home)
        # 加入旧的cookies
        cookies = json.loads(baidu_account.cookies)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)

        # 检查cookies
        if input('检查cookies是否有效: ') == 'y':
            driver.get(wenku_home)
            sleep(30)
            exit(0)

        # 再退出登录
        driver.get(logout)

        # 百度云登录用户名输入框
        username_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_4__userName'))
        )
        # 百度云登录密码输入框
        password_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_4__password'))
        )
        # 百度云登录按钮
        login_button = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_4__submit'))
        )

        username_input.send_keys(baidu_account.username)
        password_input.send_keys(baidu_account.password)
        login_button.click()
        # 等待跳转进百度云
        sleep(5)
        driver.get(wenku_home)

        try:
            nickname = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[@id='userNameCon']/span"))
            ).text.strip()
        except TimeoutException:
            nickname = None
        if nickname == baidu_account.nickname:
            baidu_cookies = driver.get_cookies()
            baidu_cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baidu_cookies.json')
            baidu_cookies_str = json.dumps(baidu_cookies)
            baidu_account.cookies = baidu_cookies_str
            baidu_account.save()
            print('ok')
        else:
            print('error')
    finally:
        driver.close()
