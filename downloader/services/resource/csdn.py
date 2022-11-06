import json
import logging
import re
from urllib import parse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.conf import settings

from downloader.models import (
    DOWNLOAD_ACCOUNT_TYPE_CSDN,
)
from downloader.serializers import UserSerializers
from downloader.services.resource.base import BaseResource
from downloader.utils import browser
from downloader.utils.alert import alert
from downloader.utils.url import remove_url_query


class CsdnResource(BaseResource):
    def __init__(self, url, user):
        url = remove_url_query(url)
        if re.match(settings.PATTERN_ITEYE, url):
            url = "https://download.csdn.net/download/" + url.split("resource/")[
                1
            ].replace("-", "/")
        super().__init__(url, user)
        self.account_type = DOWNLOAD_ACCOUNT_TYPE_CSDN

    def parse(self) -> None:
        headers = {
            "authority": "download.csdn.net",
            "referer": "https://download.csdn.net/",
            "user-agent": browser.get_random_ua(),
        }
        with requests.get(self.url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                if r.status_code == requests.codes.not_found:
                    logging.warning(f"resource not found: {self.url}")

            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.text, "lxml")

                need_pay = is_need_pay(soup)
                tags = [tag.text for tag in soup.select("div.tags a")]

                # 版权受限，无法下载
                # https://download.csdn.net/download/c_baby123/10791185
                copyright_limited = (
                    len(soup.select("div.resource_box a.copty-btn")) != 0
                )
                can_download = not copyright_limited and not need_pay
                if can_download:
                    point = settings.CSDN_POINT
                else:
                    point = None

                info = soup.select("div.info-box span")
                size = ""
                file_type = ""
                if len(info) == 12:
                    size = info[9].text
                    file_type = info[10].text
                elif len(info) == 9:
                    size = info[6].text
                    file_type = info[7].text
                elif len(info) == 11:
                    size = info[8].text
                    file_type = info[9].text
                else:
                    logging.error(
                        f"failed to get size or file_type: {info.source.text}"
                    )

                el = soup.find("h1", class_="el-tooltip d-i fs-xxl line-2 va-middle")
                if el and isinstance(el, Tag):
                    title = el.text.strip()

                desc = soup.select("p.detail-desc")
                if len(desc) > 0:
                    desc = desc[0].text

                self.resource = {
                    "title": title,
                    "desc": desc,
                    "tags": tags,
                    "file_type": file_type,
                    "point": point,
                    "size": size,
                    "need_pay": need_pay,
                    "copyright_limited": copyright_limited,
                }

    def _update_download_account(self):
        self.download_account_config["today_download_count"] = (
            self.download_account_config.get("today_download_count", 0) + 1
        )
        self.download_account.config = json.dumps(self.download_account_config)
        self.download_account.save()

    def _download(self):
        # 判断账号当天下载数
        if self.download_account_config.get("today_download_count", 0) >= 20:
            self.err = "下载次数达到上限"
            alert("CSDN下载次数达到上限", user=UserSerializers(self.user).data, url=self.url)
            return

        try:
            resource_id = self.url.split("/")[-1]
            headers = {
                "cookie": self.download_account_config.get("cookie", ""),
                "user-agent": browser.get_random_ua(),
                "referer": self.url,  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
            }
            pre_download_url = (
                f"https://download.csdn.net/source/download?source_id={resource_id}"
            )
            with requests.get(pre_download_url, headers=headers) as r:
                if r.status_code != requests.codes.ok:
                    self.err = "下载失败"
                    alert(
                        "CSDN资源下载失败",
                        url=self.url,
                        user=UserSerializers(self.user).data,
                        status_code=r.status_code,
                        response=r.text,
                        pre_download_url=pre_download_url,
                    )
                    return

                resp = r.json()
                if resp.get("code", None) != requests.codes.ok:
                    self.err = "下载失败"
                    alert(
                        "CSDN资源下载失败",
                        url=self.url,
                        user=UserSerializers(self.user).data,
                        status_code=r.status_code,
                        response=r.text,
                        pre_download_url=pre_download_url,
                    )
                    return

                download_url = resp["data"]

            self._update_download_account()

            with requests.get(download_url, headers=headers, stream=True) as r:
                if r.status_code != requests.codes.ok:
                    self.err = "下载失败"
                    alert(
                        "CSDN资源下载失败",
                        url=self.url,
                        user=UserSerializers(self.user).data,
                        status_code=r.status_code,
                        response=r.text,
                        pre_download_url=pre_download_url,
                        download_url=download_url,
                    )
                    return

                self.filename = parse.unquote(
                    r.headers["Content-Disposition"].split('"')[1]
                )
                self.write_file(r)

        except Exception as e:
            alert(
                "CSDN资源下载失败",
                url=self.url,
                user=UserSerializers(self.user).data,
                status_code=r.status_code,
                response=r.text,
                exception=e,
            )
            self.err = "下载失败"


def is_need_pay(soup: BeautifulSoup) -> bool:
    """
    判断是否是付费资源
    """
    items = soup.select("div#downloadBtn span.va-middle")
    if len(items) == 0:
        return False
    return items[0].text.find("¥") != -1
