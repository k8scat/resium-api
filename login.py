# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import json
import time

from selenium import webdriver

cookies_file = 'cookies.json'

if __name__ == '__main__':
    # 扫码登录
    login_url = 'https://passport.csdn.net/login'

    driver = webdriver.Chrome()
    try:
        driver.get(login_url)

        # 延迟60秒
        time.sleep(30)

        # 获取到cookies
        cookies = driver.get_cookies()
        # 判断是否登录成功
        for c in cookies:
            if c['name'] == 'UserName':
                # 登录成功则保存cookies
                json_cookies = json.dumps(cookies)
                with open(cookies_file, 'w') as f:
                    f.write(json_cookies)
    finally:
        driver.close()
