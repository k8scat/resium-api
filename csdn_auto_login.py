# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/17

"""
import json
import os
from time import sleep

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

github_username = 'hsowan-me'
github_password = 'holdon7868'
csdn_phone = '17770040362'
csdn_username = 'weixin_45152242'


def csdn_auto_login():
    csdn_github_oauth_url = 'https://github.com/login?client_id=4bceac0b4d39cf045157&return_to=%2Flogin%2Foauth%2Fauthorize%3Fclient_id%3D4bceac0b4d39cf045157%26redirect_uri%3Dhttps%253A%252F%252Fpassport.csdn.net%252Faccount%252Flogin%253FpcAuthType%253Dgithub%2526state%253Dtest'

    # driver = webdriver.Chrome()

    selenium_server = 'http://139.199.71.19:4444/wd/hub'
    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=selenium_server, desired_capabilities=caps)
    try:
        # 登录GitHub
        driver.get("https://github.com/login")

        login_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'login_field'))
        )
        login_field.send_keys(github_username)

        password = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'password'))
        )
        password.send_keys(github_password)

        password.send_keys(Keys.ENTER)

        def github_login_verify():
            # GitHub登录设备验证
            device_verification_code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'otp'))
            )
            dv_code = input('Device verification code: ')
            device_verification_code_input.send_keys(dv_code)
            device_verification_code_input.send_keys(Keys.ENTER)

        if input('是否需要GitHub邮箱验证码: ') == 'y':
            github_login_verify()

        driver.get(csdn_github_oauth_url)

        def csdn_login_verify():
            """
            CSDN异地登录验证

            :return:
            """
            # 手机号输入框
            phone = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'phone'))
            )
            phone.send_keys(csdn_phone)

            # 发送验证码按钮
            send_code_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button.btn-confirm'))
            )
            send_code_button.click()

            # 验证码输入框
            code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'code'))
            )
            code = input('CSDN手机验证码: ')
            code_input.send_keys(code)

            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.form-submit > button'))
            )
            submit_button.click()

        if input('是否需要CSDN手机验证码: ') == 'y':
            csdn_login_verify()

        return driver.get_cookies()

    finally:
        driver.close()


if __name__ == '__main__':
    cookies = csdn_auto_login()
    cookies_str = json.dumps(cookies)
    cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csdn_cookies.json')
    # 判断是否登录成功
    for c in cookies:
        if c['value'] == csdn_username:
            # 登录成功则保存cookies
            cookies_str = json.dumps(cookies)
            with open(cookies_file, 'w') as f:
                f.write(cookies_str)
