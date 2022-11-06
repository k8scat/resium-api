import logging
import os
import re
import uuid

import requests
from PIL import Image
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.conf import settings
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.services.resource.base import BaseResource
from downloader.utils import browser, selenium
from downloader.utils.browser import check_download
from downloader.utils.image_recognition import predict_code
from downloader.utils.url import remove_url_query


class ZhiwangResource(BaseResource):
    def __init__(self, url, user):
        url = remove_url_query(url)
        super().__init__(url, user)

    def parse(self):
        headers = {"referer": self.url, "user-agent": browser.get_random_ua()}
        with requests.get(self.url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "资源获取失败"
                return

            try:
                soup = BeautifulSoup(r.text, "lxml")
                tags = [tag.string.strip()[:-1] for tag in soup.select("p.keywords a")]
                title = soup.select("div.wxTitle h2")
                if len(title) > 0:
                    title = title[0].text

                desc = ""
                el = soup.find("span", attrs={"id": "ChDivSummary"})
                if el and isinstance(el, Tag):
                    desc = el.string

                has_pdf = not not soup.find("a", attrs={"id": "pdfDown"})
                self.resource = {
                    "title": title,
                    "desc": desc,
                    "tags": tags,
                    "pdf_download": has_pdf,  # 是否支持pdf下载
                    "point": settings.ZHIWANG_POINT,
                }

            except Exception as e:
                logging.error(e)
                self.err = "资源获取失败"
                return

    def _download(self):
        # url = resource_url.replace('https://kns.cnki.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn')
        vpn_url = re.sub(
            r"http(s)?://kns(8)?\.cnki\.net",
            "http://kns-cnki-net.wvpn.ncu.edu.cn",
            self.url,
        )

        driver = selenium.get_driver(self.unique_folder, load_images=True)
        try:
            driver.get("http://wvpn.ncu.edu.cn/users/sign_in")
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "user_login"))
            )
            username_input.send_keys(settings.NCU_VPN_USERNAME)
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "user_password"))
            )
            password_input.send_keys(settings.NCU_VPN_PASSWORD)
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[@class='col-md-6 col-md-offset-6 login-btn']/input",
                    )
                )
            )
            submit_button.click()

            driver.get(vpn_url)
            driver.refresh()

            try:
                # pdf下载
                download_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "pdfDown"))
                )
            except TimeoutException:
                self.err = "该文献不支持下载PDF"
                return

            # 获取下载链接
            download_link = download_button.get_attribute("href")
            # 访问下载链接
            driver.get(download_link)
            try:
                # 获取验证码图片
                code_image = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.ID, "vImg"))
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
                driver.get_screenshot_as_file(settings.ZHIWANG_SCREENSHOT_IMAGE)

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
                        EC.presence_of_element_located((By.ID, "vcode"))
                    )
                    code_input.send_keys(code)
                    submit_code_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//dl[@class='c_verify-code']/dd/button")
                        )
                    )
                    submit_code_button.click()

            finally:
                filename = check_download(self.save_dir)
                if filename:
                    self.filename = filename
                    file = os.path.splitext(self.filename)
                    self.filename_uuid = str(uuid.uuid1()) + file[1]
                    self.filepath = os.path.join(self.save_dir, self.filename_uuid)

                else:
                    self.err = "下载失败"

        except Exception as e:
            logging.error(e)
            self.err = "下载失败"

        finally:
            driver.close()
