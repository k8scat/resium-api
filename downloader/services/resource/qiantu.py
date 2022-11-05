import logging
import os
import uuid

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from downloader.models import QiantuAccount, PointRecord
from downloader.services.resource import BaseResource
from downloader.utils import ding, get_random_ua


class QiantuResource(BaseResource):
    def __init__(self, url, user):
        super().__init__(url, user)

    def _init_download_account(self):
        """初始下载账号"""
        try:
            self.account = QiantuAccount.objects.get(is_enabled=True)
        except QiantuAccount.DoesNotExist:
            return requests.codes.server_error, "[千图网] 没有可用账号"

    def parse(self):
        with requests.get(self.url) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, "lxml")
                    title = soup.select("span.pic-title.fl")[0].string
                    info = soup.select("div.material-info p")
                    size = info[2].string.replace("文件大小：", "")
                    # Tag有find方法，但没有select方法
                    file_type = info[4].find("span").contents[0]
                    tags = [tag.string for tag in soup.select("div.mainRight-tagBox a")]
                    self.resource = {
                        "title": title,
                        "size": size,
                        "tags": tags,
                        "desc": "",
                        "file_type": file_type,
                        "point": settings.QIANTU_POINT,
                    }
                    return requests.codes.ok, self.resource
                except Exception as e:
                    ding(
                        "资源获取失败",
                        error=e,
                        logger=logging.error,
                        uid=self.user.uid,
                        resource_url=self.url,
                        need_email=True,
                    )
                    return requests.codes.server_error, "资源获取失败"

    def _download(self):
        headers = {
            "cookie": self.account.cookies,
            "referer": self.url,
            "user-agent": get_random_ua(),
        }
        download_url = self.url.replace(
            "https://www.58pic.com/newpic/", "https://dl.58pic.com/"
        )
        with requests.get(download_url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "下载失败"
                return

            try:
                soup = BeautifulSoup(r.text, "lxml")
                download_url = soup.select("a.clickRecord.autodown")[0]["href"]
                self.filename = download_url.split("?")[0].split("/")[-1]
                file = os.path.splitext(self.filename)
                self.filename_uuid = str(uuid.uuid1()) + file[1]
                self.filepath = os.path.join(self.save_dir, self.filename_uuid)
                with requests.get(download_url, stream=True, headers=headers) as r2:
                    if r2.status_code != requests.codes.ok:
                        self.err = "下载失败"
                        return

                    point = self.resource["point"]
                    self.user.point -= point
                    self.user.used_point += point
                    self.user.save()
                    PointRecord(
                        user=self.user,
                        used_point=point,
                        comment="下载千图网资源",
                        url=self.url,
                        point=self.user.point,
                    ).save()

                    with open(self.filepath, "wb") as f:
                        for chunk in r2.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)

            except Exception as e:
                logging.error(e)
                self.err = "下载失败"
