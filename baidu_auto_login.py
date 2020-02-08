# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/29

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


if __name__ == '__main__':
    baidu_username = '15216267867'
    baidu_password = 'Holdon@777!'
    baidu_nickname = '林疯158'

    cloud_login_url = 'https://login.bce.baidu.com/'
    console = 'https://console.bce.baidu.com/'
    wenku_home = 'https://wenku.baidu.com/'
    logout = 'https://passport.baidu.com/?logout&aid=7&u=https%3A//login.bce.baidu.com/'

    # driver = webdriver.Chrome()

    selenium_server = 'http://139.199.71.19:4444/wd/hub'
    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=selenium_server, desired_capabilities=caps)

    try:
        # 先访问百度首页, 否则直接登录百度网盘的话, 百度依旧会需要验证登录
        driver.get(wenku_home)
        # 加入旧的cookies
        with open('baidu_cookies.json', 'r', encoding='utf-8') as f:
            cookies = json.loads(f.read())
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)

        # 检验cookies
        # driver.get(wenku_home)
        # sleep(60)

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

        username_input.send_keys(baidu_username)
        password_input.send_keys(baidu_password)
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
        if nickname == baidu_nickname:
            baidu_cookies = driver.get_cookies()
            baidu_cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baidu_cookies.json')
            with open(baidu_cookies_file, 'w') as f:
                baidu_cookies_str = json.dumps(baidu_cookies)
                f.write(baidu_cookies_str)
        else:
            print(nickname)
    finally:
        driver.close()
