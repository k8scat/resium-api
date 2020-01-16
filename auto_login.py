# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/17

"""
import time

from selenium import webdriver
from urllib.parse import unquote


if __name__ == '__main__':
    driver = webdriver.Chrome()
    try:
        driver.get("https://passport.csdn.net/v1/register/authorization?authType=github")
        driver.find_element_by_id("login_field").clear()
        driver.find_element_by_id("login_field").send_keys("hsowan-me")
        driver.find_element_by_id("password").click()
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys("holdon7868")
        driver.find_element_by_name("commit").click()
        driver.get('https://download.csdn.net/')
        time.sleep(60)
    finally:
        driver.close()
