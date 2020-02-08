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
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

if __name__ == '__main__':
    wenku_home = 'https://wenku.baidu.com/'
    baidu_home = 'https://www.baidu.com/'
    options = webdriver.ChromeOptions()
    prefs = {
        "download.prompt_for_download": False,
        'download.default_directory': '/Users/mac/workspace/CSDNBot/download/',  # 下载目录
        "plugins.always_open_pdf_externally": True,
        'profile.default_content_settings.popups': 0,  # 设置为0，禁止弹出窗口
        'profile.default_content_setting_values.images': 2,  # 禁止图片加载
    }
    options.add_experimental_option('prefs', prefs)

    # 线上使用selenium server
    # caps = DesiredCapabilities.CHROME
    # driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps, options=options)

    # 本地图形界面自动化测试
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(baidu_home)
        # 从文件中获取到cookies
        wenku_cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baidu_cookies.json')
        with open(wenku_cookies_file, 'r', encoding='utf-8') as f:
            cookies = json.loads(f.read())
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)

        resource_url = 'https://wenku.baidu.com/view/8ed046a1b80d6c85ec3a87c24028915f814d8400.html'
        driver.get(resource_url)

        # VIP免费文档 共享文档 VIP专享文档 付费文档 VIP尊享8折文档
        doc_tag = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'bd doc-reader')]/div/div[contains(@style, 'display: block;')]/span"))
        ).text
        if doc_tag not in ['VIP免费文档', '共享文档', 'VIP专享文档']:
            print('此类资源无法下载: ' + doc_tag)
            exit(0)

        # 显示下载对话框的按钮
        show_download_modal_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.reader-download.btn-download'))
        )
        show_download_modal_button.click()

        # 下载按钮
        try:
            download_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.dialog-inner.tac > a.ui-bz-btn-senior.btn-diaolog-downdoc'))
            )
            print('首次下载')
            # 取消转存网盘
            cancel_wp_upload_check = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.wpUpload input'))
            )
            cancel_wp_upload_check.click()
        except TimeoutException:
            print('已转存过此文档')
            download_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, 'WkDialogOk'))
            )

        download_button.click()
        sleep(30)
    finally:
        driver.quit()
