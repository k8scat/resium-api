import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.conf import settings

from downloader.models import DOWNLOAD_ACCOUNT_TYPE_QIANTU
from downloader.serializers import UserSerializers
from downloader.services.resource.base import BaseResource
from downloader.utils import browser
from downloader.utils.alert import alert
from downloader.utils.url import remove_url_query


class QiantuResource(BaseResource):
    def __init__(self, url, user):
        url = remove_url_query(url)
        super().__init__(url, user)
        self.download_account_type = DOWNLOAD_ACCOUNT_TYPE_QIANTU

    def type(self) -> str:
        return "qiantu"

    def parse(self):
        with requests.get(self.url) as r:
            if r.status_code != requests.codes.ok:
                self.err = "资源获取失败"
                alert(
                    "千图网资源获取失败",
                    user=UserSerializers(self.user).data,
                    url=self.url,
                    status_code=r.status_code,
                    response=r.text,
                )
                return

            try:
                soup = BeautifulSoup(r.text, "lxml")

                title = ""
                el = soup.find("title")
                if el and isinstance(el, Tag):
                    title = el.text

                desc = ""
                el = soup.find("meta", attrs={"name": "description"})
                if el and isinstance(el, Tag):
                    desc = el.get("content", "")

                self.resource = {
                    "title": title,
                    "desc": desc,
                    "point": settings.QIANTU_POINT,
                }

            except Exception as e:
                alert(
                    "千图网资源获取失败",
                    exception=e,
                    user=UserSerializers(self.user).data,
                    url=self.url,
                )

    def _download(self):
        headers = {
            "cookie": self.download_account_config.get("cookie", ""),
            "referer": self.url,
            "user-agent": browser.get_random_ua(),
        }
        pre_download_url = self.url.replace(
            "https://www.58pic.com/newpic/", "https://dl.58pic.com/"
        )
        with requests.get(pre_download_url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "下载失败"
                alert(
                    "千图网资源下载失败",
                    status_code=r.status_code,
                    response=r.text,
                    url=self.url,
                    user=UserSerializers(self.user).data,
                    pre_download_url=pre_download_url,
                )
                return

            try:
                soup = BeautifulSoup(r.text, "lxml")
                download_url = soup.select("a.clickRecord.autodown")[0]["href"]
                self.filename = download_url.split("?")[0].split("/")[-1]
                with requests.get(download_url, stream=True, headers=headers) as r2:
                    if r2.status_code != requests.codes.ok:
                        self.err = "下载失败"
                        alert(
                            "千图网资源下载失败",
                            status_code=r2.status_code,
                            response=r2.text,
                            url=self.url,
                            user=UserSerializers(self.user).data,
                            download_url=download_url,
                            pre_download_url=pre_download_url,
                        )
                        return

                    self.write_file(r2)

            except Exception as e:
                alert(
                    "千图网资源下载失败",
                    url=self.url,
                    user=UserSerializers(self.user).data,
                    exception=e,
                    pre_download_url=pre_download_url,
                )
                self.err = "下载失败"
