import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.conf import settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import (
    DocerPreviewImage,
    DOWNLOAD_ACCOUNT_TYPE_DOCER,
)
from downloader.serializers import UserSerializers
from downloader.services.resource.base import BaseResource
from downloader.utils import browser, selenium
from downloader.utils.alert import alert
from downloader.utils.url import remove_url_query


class DocerResource(BaseResource):
    def __init__(self, url, user):
        url = remove_url_query(url)
        super().__init__(url, user)
        self.download_account_type = DOWNLOAD_ACCOUNT_TYPE_DOCER

    def parse(self):
        headers = {
            "referer": "https://www.docer.com/",
            "user-agent": browser.get_random_ua(),
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "资源获取失败"
                alert(
                    "稻壳模板资源解析失败",
                    status_code=r.status_code,
                    response=r.text,
                    url=self.url,
                    user=UserSerializers(self.user).data,
                )
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
                driver = selenium.get_driver()
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

            title = ""
            el = soup.find("h1", class_="preview-info_title")
            if el and isinstance(el, Tag):
                title = el.string

            file_type = ""
            els = soup.select("span.m-crumbs-path a")
            if len(els) > 0:
                file_type = els[0].text

            self.resource = {
                "title": title,
                "tags": tags,
                "file_type": file_type,
                # soup.find('meta', attrs={'name': 'Description'})['content']
                "desc": "",
                "point": settings.DOCER_POINT,
                "is_docer_vip_doc": r.text.count("类型：VIP模板") > 0,
                "preview_images": preview_images,
            }

    def _download(self):
        resource_id = self.url.split("/")[-1]
        api = f"https://www.docer.com/detail/dl?id={resource_id}"
        headers = {
            "cookie": self.download_account_config.get("cookie", ""),
            "user-agent": browser.get_random_ua(),
        }
        # 如果cookies失效，r.json()会抛出异常
        with requests.get(api, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "资源获取失败"
                alert(
                    "稻壳模板资源下载失败",
                    status_code=r.status_code,
                    response=r.text,
                    url=self.url,
                    api=api,
                    user=UserSerializers(self.user).data,
                )
                return

            try:
                resp = r.json()
                if resp.get("result", None) != "ok":
                    self.err = "下载失败"
                    alert(
                        "稻壳模板资源下载失败",
                        status_code=r.status_code,
                        response=r.text,
                        url=self.url,
                        api=api,
                        user=UserSerializers(self.user).data,
                    )
                    return

                download_url = resp["data"]
                self.filename = download_url.split("/")[-1]
                with requests.get(download_url, stream=True) as r2:
                    if r2.status_code != requests.codes.ok:
                        self.err = "下载失败"
                        alert(
                            "稻壳模板资源下载失败",
                            status_code=r2.status_code,
                            response=r2.text,
                            url=self.url,
                            api=api,
                            download_url=download_url,
                            user=UserSerializers(self.user).data,
                        )
                        return

                    self.write_file(r2)

            except Exception as e:
                alert(
                    "稻壳模板资源下载失败",
                    status_code=r.status_code,
                    response=r.text,
                    url=self.url,
                    api=api,
                    user=UserSerializers(self.user).data,
                    exception=e,
                )
                alert("资源下载失败")
                self.err = "下载失败"
                return
