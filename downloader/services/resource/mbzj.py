import re

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from downloader.models import DOWNLOAD_ACCOUNT_TYPE_MBZJ
from downloader.serializers import UserSerializers
from downloader.services.resource.base import BaseResource
from downloader.utils import browser
from downloader.utils.alert import alert
from downloader.utils.url import remove_url_query


class MbzjResource(BaseResource):
    def __init__(self, url, user):
        url = remove_url_query(url)
        url = re.sub(r"\.shtml.*", ".shtml", url)
        super().__init__(url, user)
        self.download_account_type = DOWNLOAD_ACCOUNT_TYPE_MBZJ

    def parse(self):
        headers = {
            "referer": "http://www.cssmoban.com/",
            "user-agent": browser.get_random_ua(),
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "资源获取失败"
                alert(
                    "模板之家资源获取失败",
                    status_code=r.status_code,
                    response=r.text,
                    user=UserSerializers(self.user).data,
                    url=self.url,
                )
                return

            soup = BeautifulSoup(r.text, "lxml")
            if self.url.count("wpthemes") > 0:
                tags = [tag.text for tag in soup.select("div.tags a")]
            else:
                tags = [tag.text for tag in soup.select("div.tags a")[:-1]]

            title = ""
            els = soup.select("div.con-right h1")
            if len(els) > 0:
                title = els[0].text

            self.resource = {
                "title": title,
                "tags": tags,
                "desc": "",
                "point": settings.MBZJ_POINT,
            }

    def _download(self):
        # 下载资源
        resource_id = self.url.split("/")[-1].split(".shtml")[0]
        pre_download_url = "http://vip.cssmoban.com/api/Down"
        payload = {
            "userid": self.download_account_config.get("user_id", ""),
            "screkey": self.download_account_config.get("secret_key", ""),
            "mobanid": resource_id,
        }
        headers = {"referer": self.url, "user-agent": browser.get_random_ua()}
        with requests.get(pre_download_url, headers=headers, data=payload) as r:
            if r.status_code != requests.codes.ok:
                self.err = "下载失败"
                alert(
                    "模板之家资源下载失败",
                    url=self.url,
                    user=UserSerializers(self.user).data,
                    status_code=r.status_code,
                    response=r.text,
                    pre_download_url=pre_download_url,
                )
                return

            resp = r.json()
            if resp.get("code", None) != 0:
                self.err = "下载失败"
                alert(
                    "模板之家资源下载失败",
                    url=self.url,
                    user=UserSerializers(self.user).data,
                    status_code=r.status_code,
                    response=r.text,
                    pre_download_url=pre_download_url,
                )
                return

            download_url = resp["data"]
            self.filename = resp["data"].split("/")[-1]
            with requests.get(download_url, stream=True) as r2:
                if r2.status_code != requests.codes.ok:
                    self.err = "下载失败"
                    alert(
                        "模板之家资源下载失败",
                        url=self.url,
                        user=UserSerializers(self.user).data,
                        status_code=r2.status_code,
                        response=r2.text,
                        pre_download_url=pre_download_url,
                        download_url=download_url,
                    )
                    return

                self.write_file(r2)
