import json
import logging
import os
import uuid
from urllib import parse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache

from downloader.models import (
    PointRecord,
    ACCOUNT_TYPE_CSDN,
)
from downloader.services.resource import BaseResource
from downloader.utils import get_random_ua


class CsdnResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

        self.account_type = ACCOUNT_TYPE_CSDN

    def parse(self):
        headers = {
            "authority": "download.csdn.net",
            "referer": "https://download.csdn.net/",
            "user-agent": get_random_ua(),
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

                title = soup.find("h1", class_="el-tooltip d-i fs-xxl line-2 va-middle")
                if title:
                    title = title.text.strip()

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
        self.download_account_config["used_count"] = (
            self.download_account_config.get("used_count", 0) + 1
        )
        self.download_account_config["valid_count"] = (
            self.download_account_config.get("valid_count", 0) + 1
        )
        self.download_account.config = json.dumps(self.download_account_config)
        self.download_account.save()

    def _download(self):
        try:
            # 判断账号当天下载数
            if self.download_account_config.get("today_download_count", 0) >= 20:
                self.err = "下载次数达到上限"
                return

            resource_id = self.url.split("/")[-1]
            headers = {
                "cookie": self.download_account_config.get("cookie", ""),
                "user-agent": get_random_ua(),
                "referer": self.url,  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
            }
            pre_download_url = (
                f"https://download.csdn.net/source/download?source_id={resource_id}"
            )
            with requests.get(pre_download_url, headers=headers) as r:
                if r.status_code != requests.codes.ok:
                    logging.error(
                        f"request {pre_download_url} failed, code: {r.status_code}, text: {r.text}"
                    )
                    self.err = "下载失败"
                    return

                resp = r.json()
                if resp.get("code", None) != requests.codes.ok:
                    logging.error(
                        f"request {pre_download_url} failed, code: {r.status_code}, text: {r.text}"
                    )
                    self.err = "下载失败"
                    return

                download_url = resp["data"]

            self._update_download_account()

            point = self.resource["point"]
            # 更新用户的剩余积分和已用积分
            self.user.point -= point
            self.user.used_point += point
            self.user.save()
            PointRecord(
                user=self.user,
                used_point=point,
                point=self.user.point,
                comment="下载CSDN资源",
                url=self.url,
            ).save()

            with requests.get(download_url, headers=headers, stream=True) as r:
                if r.status_code != requests.codes.ok:
                    raise Exception(f"failed to download: {r.text}")

                self.filename = parse.unquote(
                    r.headers["Content-Disposition"].split('"')[1]
                )
                file = os.path.splitext(self.filename)
                self.filename_uuid = str(uuid.uuid1()) + file[1]
                self.filepath = os.path.join(self.save_dir, self.filename_uuid)
                # 写入文件，用于线程上传资源到OSS
                with open(self.filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

        except Exception as e:
            logging.error(e)
            self.err = "下载失败"
        finally:
            cache.delete(settings.CSDN_DOWNLOADING_KEY)


def is_need_pay(soup: BeautifulSoup) -> bool:
    """
    判断是否是付费资源
    """
    items = soup.select("div#downloadBtn span.va-middle")
    if len(items) == 0:
        return False
    return items[0].text.find("¥") != -1
