import logging
import os
import uuid

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import (
    DocerPreviewImage,
    PointRecord,
)
from downloader.services.resource import BaseResource
from downloader.utils import get_random_ua, get_driver


class DocerResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def parse(self):
        headers = {"referer": "https://www.docer.com/", "user-agent": get_random_ua()}
        with requests.get(self.url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "资源获取失败"
                return

            soup = BeautifulSoup(r.text, "lxml")
            tags = [tag.text for tag in soup.select("li.preview__labels-item.g-link a")]
            if "展开更多" in tags:
                tags = tags[:-1]

            # 获取所有的预览图片
            preview_images = DocerPreviewImage.objects.filter(
                resource_url=self.url
            ).all()
            if len(preview_images) > 0:
                preview_images = [
                    {
                        "url": preview_image.url,
                        "alt": preview_image.alt,
                    }
                    for preview_image in preview_images
                ]
            else:
                driver = get_driver()
                try:
                    driver.get(self.url)
                    all_images = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, '//ul[@class="preview__img-list"]//img')
                        )
                    )
                    preview_images = []
                    preview_image_models = []
                    for image in all_images:
                        image_url = image.get_attribute("data-src")
                        image_alt = image.get_attribute("alt")
                        preview_images.append({"url": image_url, "alt": image_alt})
                        preview_image_models.append(
                            DocerPreviewImage(
                                resource_url=self.url, url=image_url, alt=image_alt
                            )
                        )
                    DocerPreviewImage.objects.bulk_create(preview_image_models)
                finally:
                    driver.close()

            self.resource = {
                "title": soup.find("h1", class_="preview-info_title").string,
                "tags": tags,
                "file_type": soup.select("span.m-crumbs-path a")[0].text,
                # soup.find('meta', attrs={'name': 'Description'})['content']
                "desc": "",
                "point": settings.DOCER_POINT,
                "is_docer_vip_doc": r.text.count("类型：VIP模板") > 0,
                "preview_images": preview_images,
            }

    def _download(self):
        resource_id = self.url.split("/")[-1]
        api = f"https://www.docer.com/detail/dl?id={resource_id}"
        headers = {"cookie": self.account.cookies, "user-agent": get_random_ua()}
        # 如果cookies失效，r.json()会抛出异常
        with requests.get(api, headers=headers) as r:
            try:
                resp = r.json()
                if resp.get("result", None) != "ok":
                    self.err = "下载失败"
                    return

                # 更新用户积分
                point = self.resource["point"]
                self.user.point -= point
                self.user.used_point += point
                self.user.save()
                PointRecord(
                    user=self.user,
                    used_point=point,
                    comment="下载稻壳模板",
                    url=self.url,
                    point=self.user.point,
                ).save()

                # 更新账号使用下载数
                self.account.used_count += 1
                self.account.save()

                download_url = resp["data"]
                self.filename = download_url.split("/")[-1]
                file = os.path.splitext(self.filename)
                self.filename_uuid = str(uuid.uuid1()) + file[1]
                self.filepath = os.path.join(self.save_dir, self.filename_uuid)
                with requests.get(download_url, stream=True) as r2:
                    if r2.status_code != requests.codes.ok:
                        self.err = "下载失败"
                        return

                    with open(self.filepath, "wb") as f:
                        for chunk in r2.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)

            except Exception as e:
                logging.error(e)
                self.err = "下载失败"
                return
