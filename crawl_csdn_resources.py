# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/12

爬取CSDN账号已下载资源

"""
import uuid

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

if __name__ == '__main__':
    options = webdriver.ChromeOptions()
    prefs = {
        "download.prompt_for_download": False,
        'download.default_directory': '/download/' + folder,  # 下载目录, 需要在docker做映射
        "plugins.always_open_pdf_externally": True,
        'profile.default_content_settings.popups': 0,  # 设置为0，禁止弹出窗口
        'profile.default_content_setting_values.images': 2,  # 禁止图片加载
    }
    options.add_experimental_option('prefs', prefs)

    caps = DesiredCapabilities.CHROME
    # 线上使用selenium server
    driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps,
                              options=options)

    try:
        # 先请求，再添加cookies
        # selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
        driver.get('https://download.csdn.net')
        # 添加cookies

    finally:
        driver.quit()

