import os
import uuid

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from downloader.models import PointRecord, ACCOUNT_TYPE_MBZJ
from downloader.services.resource import BaseResource
from downloader.utils import get_random_ua


class MbzjResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

        self.account_type = ACCOUNT_TYPE_MBZJ

    def parse(self):
        headers = {"referer": "http://www.cssmoban.com/", "user-agent": get_random_ua()}
        with requests.get(self.url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.content.decode(), "lxml")
                if self.url.count("wpthemes") > 0:
                    tags = [tag.text for tag in soup.select("div.tags a")]
                else:
                    tags = [tag.text for tag in soup.select("div.tags a")[:-1]]

                self.resource = {
                    "title": soup.select("div.con-right h1")[0].text,
                    "tags": tags,
                    "desc": "",
                    "point": settings.MBZJ_POINT,
                }
                return requests.codes.ok, self.resource

            return requests.codes.server_error, "资源获取失败"

    def _download(self):
        # 下载资源
        resource_id = self.url.split("/")[-1].split(".shtml")[0]
        download_url = "http://vip.cssmoban.com/api/Down"
        payload = {
            "userid": self.download_account_config.get("user_id", ""),
            "screkey": self.download_account_config.get("secret_key", ""),
            "mobanid": resource_id,
        }
        headers = {"referer": self.url, "user-agent": get_random_ua()}
        with requests.get(download_url, headers=headers, data=payload) as r:
            resp = r.json()
            if resp.get("code", None) != 0:
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
                comment="下载模板之家模板",
                url=self.url,
                point=self.user.point,
            ).save()

            download_url = resp["data"]
            self.filename = resp["data"].split("/")[-1]
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
