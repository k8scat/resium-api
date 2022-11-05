import json
import logging
import os
import re
import uuid
from urllib import parse

import requests
from django.conf import settings

from downloader.models import PointRecord
from downloader.services.resource import BaseResource
from downloader.utils import get_random_ua


class WenkuResource(BaseResource):
    def __init__(self, url, user, doc_id):
        super().__init__(url, user)
        self.doc_id = doc_id

    def parse(self):
        """
        资源信息获取地址: https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id=
        """
        logging.info(f"百度文库文档ID: {self.doc_id}")

        get_doc_info_url = f"https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id={self.doc_id}"
        get_vip_free_doc_url = (
            f"https://wenku.baidu.com/user/interface/getvipfreedoc?doc_id={self.doc_id}"
        )
        headers = {"user-agent": get_random_ua()}
        with requests.get(get_doc_info_url, headers=headers, verify=False) as r:
            if r.status_code != requests.codes.OK:
                return requests.codes.server_error, "资源获取失败"

            try:
                data = json.loads(r.content.decode()[7:-1])
                doc_info = data["docInfo"]
                # 判断是否是VIP专享文档
                if doc_info.get("professionalDoc", None) == 1:
                    point = settings.WENKU_SPECIAL_DOC_POINT
                    wenku_type = "VIP专项文档"
                elif doc_info.get("isPaymentDoc", None) == 0:
                    with requests.get(
                        get_vip_free_doc_url, headers=headers, verify=False
                    ) as r2:
                        try:
                            if r2.status_code != requests.codes.ok:
                                self.err = "资源获取失败"
                                return

                            resp = r2.json()
                            if resp["status"]["code"] != 0:
                                self.err = "资源获取失败"
                                return

                            if resp["data"]["is_vip_free_doc"]:
                                point = settings.WENKU_VIP_FREE_DOC_POINT
                                wenku_type = "VIP免费文档"
                            else:
                                point = settings.WENKU_SHARE_DOC_POINT
                                wenku_type = "共享文档"

                        except Exception as e:
                            logging.error(e)
                            self.err = "资源获取失败"
                            return
                else:
                    point = None
                    wenku_type = "付费文档"

                file_type = doc_info.get("docType", "")
                file_type = settings.FILE_TYPES.get(file_type, "UNKNOWN")
                self.resource = {
                    "title": doc_info.get("docTitle", ""),
                    "tags": doc_info.get("newTagArray", []),
                    "desc": doc_info.get("docDesc", ""),
                    "file_type": file_type,
                    "point": point,
                    "wenku_type": wenku_type,
                }

            except Exception as e:
                logging.error(e)
                self.err = "资源获取失败"

    def _download(self):
        # 更新用户积分
        point = self.resource["point"]
        self.user.point -= point
        self.user.used_point += point
        self.user.save()
        PointRecord(
            user=self.user,
            point=self.user.point,
            comment="下载百度文库文档",
            url=self.url,
            used_point=point,
        ).save()

        api = f"{settings.DOWNHUB_SERVER}/parse/wenku"
        payload = {"url": self.url}
        headers = {"token": settings.DOWNHUB_TOKEN}
        with requests.post(api, json=payload, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "下载失败"
                return

            try:
                download_url = r.json().get("data", None)
                if not download_url:
                    self.err = "下载失败"
                    return

                for queryItem in (
                    parse.urlparse(parse.unquote(download_url))
                    .query.replace(" ", "")
                    .split(";")
                ):
                    if re.match(r'^filename=".*"$', queryItem):
                        self.filename = queryItem.split('"')[1]
                        break
                    else:
                        continue

                if not self.filename:
                    self.err = "下载失败"
                    return

                file = os.path.splitext(self.filename)
                self.filename_uuid = str(uuid.uuid1()) + file[1]
                self.filepath = os.path.join(self.save_dir, self.filename_uuid)
                with requests.get(download_url, stream=True) as r2:
                    if r2.status_code == requests.codes.OK:
                        with open(self.filepath, "wb") as f:
                            for chunk in r2.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        return

                    self.err = "下载失败"
                    return

            except Exception as e:
                logging.error(e)
                self.err = "下载失败"
