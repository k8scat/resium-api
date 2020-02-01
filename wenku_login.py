# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/29

"""
import json
import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys


if __name__ == '__main__':

    wenku_login_url = 'https://passport.baidu.com/v2/?login'
    wenku_home = 'https://wenku.baidu.com/'

    driver = webdriver.Chrome()

    # selenium_server = 'http://49.235.161.70:6666/wd/hub'
    # caps = DesiredCapabilities.CHROME
    # driver = webdriver.Remote(command_executor=selenium_server, desired_capabilities=caps)

    try:
        driver.get(wenku_login_url)

        # 用户名登录按钮
        username_login_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_3__footerULoginBtn'))
        )
        username_login_button.click()

        # 用户名输入框
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_3__userName'))
        )
        username_input.send_keys('hsowan@aliyun.com')

        # 密码输入框
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'TANGRAM__PSP_3__password'))
        )
        password_input.send_keys('Holdon@7868')

        # 回车登录
        password_input.send_keys(Keys.ENTER)

        if driver.current_url == 'https://passport.baidu.com/v2/?login':
            # 验证登录
            verify_code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'TANGRAM__21__input_softtoken'))
            )
            verify_code = input('动态令牌: ')
            verify_code_input.send_keys(verify_code)
            verify_code_input.send_keys(Keys.ENTER)

        # 需要等待登录完成
        sleep(10)

        driver.get(wenku_home)
        wenku_cookies = driver.get_cookies()
        print(wenku_cookies)
        wenku_cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wenku_cookies.json')
        with open(wenku_cookies_file, 'w') as f:
            wenku_cookies_str = json.dumps(wenku_cookies)
            f.write(wenku_cookies_str)

        sleep(100)
    finally:
        driver.close()
