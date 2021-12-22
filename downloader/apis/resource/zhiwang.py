import logging
import os
import re
import uuid
from threading import Thread

import requests
from PIL import Image
from bs4 import BeautifulSoup
from django.conf import settings
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from downloader.apis.resource.resource import BaseResource
from downloader.models import PointRecord
from downloader.utils import get_random_ua, ding, get_driver, predict_code, check_download, save_resource


class ZhiwangResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        """
        需要注意的是知网官方网站和使用了VPN访问的网站是不一样的

        :return:
        """

        headers = {
            'referer': self.url,
            'user-agent': get_random_ua()
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    # 获取标签
                    tags = []
                    for tag in soup.select('p.keywords a'):
                        tags.append(tag.string.strip()[:-1])

                    title = soup.select('div.wxTitle h2')[0].text
                    desc = soup.find(
                        'span', attrs={'id': 'ChDivSummary'}).string
                    has_pdf = True if soup.find(
                        'a', attrs={'id': 'pdfDown'}) else False
                    self.resource = {
                        'title': title,
                        'desc': desc,
                        'tags': tags,
                        'pdf_download': has_pdf,  # 是否支持pdf下载
                        'point': settings.ZHIWANG_POINT
                    }
                    return requests.codes.ok, self.resource
                except Exception as e:
                    ding('资源获取失败',
                         error=e,
                         logger=logging.error,
                         uid=self.user.uid,
                         resource_url=self.url,
                         need_email=True)
                    return requests.codes.server_error, '资源获取失败'
            else:
                return requests.codes.server_error, '资源获取失败'

    def __download(self):
        self._before_download()

        status, result = self.parse()
        if status != requests.codes.ok:
            return status, result

        point = self.resource['point']
        if self.user.point < point:
            return 5000, '积分不足，请进行捐赠支持。'

        # url = resource_url.replace('https://kns.cnki.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn')
        vpn_url = re.sub(r'http(s)?://kns(8)?\.cnki\.net',
                         'http://kns-cnki-net.wvpn.ncu.edu.cn', self.url)

        driver = get_driver(self.unique_folder, load_images=True)
        try:
            driver.get('http://wvpn.ncu.edu.cn/users/sign_in')
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'user_login'))
            )
            username_input.send_keys(settings.NCU_VPN_USERNAME)
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'user_password'))
            )
            password_input.send_keys(settings.NCU_VPN_PASSWORD)
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//div[@class='col-md-6 col-md-offset-6 login-btn']/input")
                )
            )
            submit_button.click()

            driver.get(vpn_url)
            driver.refresh()

            try:
                # pdf下载
                download_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, 'pdfDown')
                    )
                )
            except TimeoutException:
                return requests.codes.bad_request, '该文献不支持下载PDF'

            self.user.point -= point
            self.user.used_point += point
            self.user.save()
            PointRecord(user=self.user, used_point=point,
                        comment='下载知网文献', url=self.url,
                        point=self.user.point).save()

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
                # 自动获取截取位置
                # left = int(code_image.location['x'])
                # print(left)
                # upper = int(code_image.location['y'])
                # print(upper)
                # right = int(code_image.location['x'] + code_image.size['width'])
                # print(right)
                # lower = int(code_image.location['y'] + code_image.size['height'])
                # print(lower)

                # 获取截图
                driver.get_screenshot_as_file(
                    settings.ZHIWANG_SCREENSHOT_IMAGE)

                # 手动设置截取位置
                left = 430
                upper = 275
                right = 620
                lower = 340
                # 通过Image处理图像
                img = Image.open(settings.ZHIWANG_SCREENSHOT_IMAGE)
                # 剪切图片
                img = img.crop((left, upper, right, lower))
                # 保存剪切好的图片
                img.save(settings.ZHIWANG_CODE_IMAGE)

                code = predict_code(settings.ZHIWANG_CODE_IMAGE)
                if code:
                    code_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, 'vcode')
                        )
                    )
                    code_input.send_keys(code)
                    submit_code_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH,
                             "//dl[@class='c_verify-code']/dd/button")
                        )
                    )
                    submit_code_button.click()
                else:
                    return requests.codes.server_error, '下载失败'

            finally:
                status, result = check_download(self.save_dir)
                if status == requests.codes.ok:
                    self.filename = result
                    file = os.path.splitext(self.filename)
                    self.filename_uuid = str(uuid.uuid1()) + file[1]
                    self.filepath = os.path.join(
                        self.save_dir, self.filename_uuid)
                    return requests.codes.ok, '下载成功'
                else:
                    return status, result

        except Exception as e:
            ding('[知网文献] 下载失败',
                 error=e,
                 uid=self.user.uid,
                 resource_url=self.url,
                 logger=logging.error,
                 need_email=True)
            return requests.codes.server_error, '下载失败'

        finally:
            driver.close()

    def get_filepath(self):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        # 保存资源
        t = Thread(target=save_resource,
                   args=(self.url, self.filename, self.filepath, self.resource, self.user))
        t.start()
        # 使用Nginx静态资源下载服务
        download_url = f'{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}'
        return requests.codes.ok, dict(filepath=self.filepath,
                                       filename=self.filename,
                                       download_url=download_url)

    def get_url(self, use_email=False):
        status, result = self.__download()
        if status != requests.codes.ok:
            return status, result

        download_url = save_resource(resource_url=self.url, resource_info=self.resource,
                                     filepath=self.filepath, filename=self.filename,
                                     user=self.user, return_url=True)
        if use_email:
            return self.send_email(download_url)

        if download_url:
            return requests.codes.ok, download_url
        else:
            return requests.codes.server_error, '下载出了点小问题，请尝试重新下载'
