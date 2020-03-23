# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/9

"""
import json
import os
from json import JSONDecodeError

import django
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()

import requests
from downloader.utils import ding
import hashlib
import time

from PIL import Image
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from django.conf import settings


def zhiwang_download(url, download_type):
    driver = webdriver.Chrome()
    try:
        driver.get('http://wvpn.ncu.edu.cn/users/sign_in')
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, 'user_login'))
        )
        username_input.send_keys('8000116092')
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, 'user_password'))
        )
        password_input.send_keys('holdon7868')
        submit_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='col-md-6 col-md-offset-6 login-btn']/input")
            )
        )
        submit_button.click()

        driver.get(url)
        driver.refresh()

        # 获取下载按钮
        if download_type == 'caj':
            # caj下载
            download_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'cajDown')
                )
            )
        elif download_type == 'pdf':
            # pdf下载
            download_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'pdfDown')
                )
            )
        else:
            return
        # 获取下载链接
        download_link = download_button.get_attribute('href')
        # 访问下载链接
        driver.get(download_link)
        try:
            # 获取验证码图片
            code_image = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located(
                    (By.ID, 'vImg')
                )
            )
            # left = int(code_image.location['x'])
            # print(left)
            # upper = int(code_image.location['y'])
            # print(upper)
            # right = int(code_image.location['x'] + code_image.size['width'])
            # print(right)
            # lower = int(code_image.location['y'] + code_image.size['height'])
            # print(lower)
        except TimeoutException:
            pass

        # 获取截图
        driver.get_screenshot_as_file(settings.SCREENSHOT_IMAGE)

        left = 430
        upper = 275
        right = 620
        lower = 340
        # 通过Image处理图像
        img = Image.open(settings.SCREENSHOT_IMAGE)
        # 剪切图片
        img = img.crop((left, upper, right, lower))
        # 保存剪切好的图片
        img.save(settings.CODE_IMAGE)

        code = predict(settings.CODE_IMAGE)
        if code:
            code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'vcode')
                )
            )
            code_input.send_keys(code)
            submit_code_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//dl[@class='c_verify-code']/dd/button")
                )
            )
            submit_code_button.click()
        else:
            return

    finally:
        driver.close()


def calc_sign(pd_id, pd_key, timestamp):
    md5 = hashlib.md5()
    md5.update((timestamp + pd_key).encode())
    csign = md5.hexdigest()

    md5 = hashlib.md5()
    md5.update((pd_id + timestamp + csign).encode())
    csign = md5.hexdigest()
    return csign


def predict(image_path):
    tm = str(int(time.time()))
    sign = calc_sign(settings.PD_ID, settings.PD_KEY, tm)
    data = {
        'user_id': settings.PD_ID,
        'timestamp': tm,
        'sign': sign,
        'predict_type': 30400,
        'up_type': 'mt'
    }
    url = 'http://pred.fateadm.com/api/capreg'
    files = {
        'img_data': ('img_data', open(image_path, 'rb').read())
    }
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'
    }
    # requests POST a Multipart-Encoded File
    # https://requests.readthedocs.io/en/master/user/quickstart/#post-a-multipart-encoded-file
    with requests.post(url, data, files=files, headers=headers) as r:
        try:
            result = r.json()
            print(result)
            if result['RetCode'] == '0':
                code = json.loads(result['RspData'])['result']
                ding(f'验证码识别成功: {code}')
                return code
            else:
                ding(f'验证码识别失败: {r.text}')
                return None
        except JSONDecodeError:
            ding(f'验证码识别失败: {r.text}')
            return None


if __name__ == '__main__':
    resource_url = 'http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/11.2625.V.20200304.0903.001.html?uid=WEEvREcwSlJHSldRa1FhdXNzY2Z1Ull0L0xSR1IrbmtSejkrY1Z5WlFNaz0=$9A4hF_YAuvQ5obgVAqNKPCYcEjKensW4IQMovwHtwkF4VYPoHbKxJw!!&v=MDM0MDRySTlIWk9zUFl3OU16bVJuNmo1N1QzZmxxV00wQ0xMN1I3cWRaK1pzRmlEbFZiM05JMTQ9SnlmRFpiRzRITkhN'
    zhiwang_download(resource_url, download_type='caj')



