# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/17

"""
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

if __name__ == '__main__':
    # driver = webdriver.Chrome()

    selenium_server = 'http://selenium:4444/wd/hub'
    caps = DesiredCapabilities.CHROME
    driver = webdriver.Remote(command_executor=selenium_server, desired_capabilities=caps)
    try:
        linkedin_login_url = 'https://www.linkedin.com/login'
        driver.get(linkedin_login_url)
        driver.find_element_by_id("username").clear()
        driver.find_element_by_id("username").send_keys("hsowan.me@gmail.com")
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys("holdon7868")
        driver.find_element_by_xpath("//button[@type='submit']").click()

        print(driver.page_source)
        print(type(driver.page_source))
        print(driver.page_source.count('万华松'))
    finally:
        driver.close()
