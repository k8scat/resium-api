# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""

import os
from time import sleep

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from downloader.models import *
from downloader.utils import *


if __name__ == '__main__':
    for resource in Resource.objects.filter(url__startswith='https://wenku.baidu.com/view/', wenku_type__isnull=True).all():
        driver = webdriver.Chrome()
        try:
            driver.get(resource.url)
            try:
                # 获取百度文库文档类型
                doc_type = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//div[@class='doc-tag-wrap super-vip']/div[contains(@style, 'block')]/span"))
                ).text
                logging.info(doc_type)
                resource.wenku_type = doc_type
                resource.save()
            except TimeoutException:
                logging.error(f'百度文库文档类型获取失败 {resource.url}')
                continue
        finally:
            driver.close()







