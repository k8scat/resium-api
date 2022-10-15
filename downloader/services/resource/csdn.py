import json
import logging
import os
import traceback
import uuid
from typing import Dict
from urllib import parse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache

from downloader.models import (
    PointRecord,
    DownloadAccount,
    ACCOUNT_TYPE_CSDN,
    STATUS_ENABLED,
)
from downloader.services.resource import BaseResource
from downloader.utils import get_random_ua, ding


class CsdnResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

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
                # 版权受限，无法下载
                # https://download.csdn.net/download/c_baby123/10791185
                copyright_limited = (
                    len(soup.select("div.resource_box a.copty-btn")) != 0
                )
                need_pay = is_need_pay(soup)
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

                tags = soup.select("div.tags a")
                title = soup.find(
                    "h1", class_="el-tooltip d-i fs-xxl line-2 va-middle"
                ).text.strip()
                desc = soup.select("p.detail-desc")[0].text
                self.resource = {
                    "title": title,
                    "desc": desc,
                    "tags": [tag.text for tag in tags],
                    "file_type": file_type,
                    "point": point,
                    "size": size,
                    "need_pay": need_pay,
                    "copyright_limited": copyright_limited,
                }

    def _init_download_account(self):
        try:
            self.download_account = DownloadAccount.objects.filter(
                type=ACCOUNT_TYPE_CSDN, status=STATUS_ENABLED
            ).first()
            if self.download_account:
                self.download_account_config: Dict = json.loads(
                    self.download_account.config
                )

                # 判断账号当天下载数
                if self.download_account_config.get("today_download_count", 0) >= 20:
                    ding(
                        f"[CSDN] 今日下载数已用完",
                        uid=self.user.uid,
                        resource_url=self.url,
                        download_account_id=self.account.get("phone", ""),
                        need_email=True,
                    )

                    self.download_account = None
                    self.download_account_config = None
        except Exception as e:
            logging.error(
                f"failed to init download account: {e}\n{traceback.format_exc()}"
            )

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
            self.parse()
            point = self.resource.get("point", None)
            if point is None:
                raise Exception("invalid point")

            # 可用积分不足
            if self.user.point < point:
                raise Exception("user point is not enough")

            self._init_download_account()
            if not self.download_account:
                raise Exception("invalid download account")

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
                    raise Exception(f"failed to download: {r.text}")

                resp = r.json()
                if resp.get("code", None) != requests.codes.ok:
                    raise Exception(f"failed to download: {r.text}")

                download_url = resp["data"]

            self._update_download_account()

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
            raise e
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
