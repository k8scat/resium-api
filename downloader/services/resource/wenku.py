import json
import re
from urllib import parse

import requests
from django.conf import settings

from downloader.serializers import UserSerializers
from downloader.services.resource.base import BaseResource
from downloader.utils import browser
from downloader.utils.alert import alert
from downloader.utils.url import remove_url_query


class WenkuResource(BaseResource):
    def __init__(self, url, user):
        url = remove_url_query(url)
        super().__init__(url, user)

    def _get_doc_id(self) -> str:
        # https://wenku.baidu.com/view/e414fc173a3567ec102de2bd960590c69ec3d8f8.html?fr=search_income2
        doc_id = self.url.split("baidu.com/view/")[1]
        if doc_id.count(".") > 0:
            doc_id = doc_id.split(".")[0]
        self.url = "https://wenku.baidu.com/view/" + doc_id + ".html"
        return doc_id

    def parse(self):
        """
        资源信息获取地址: https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id=
        """

        doc_id = self._get_doc_id()
        get_doc_info_url = (
            f"https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id={doc_id}"
        )
        get_vip_free_doc_url = (
            f"https://wenku.baidu.com/user/interface/getvipfreedoc?doc_id={doc_id}"
        )
        headers = {"user-agent": browser.get_random_ua()}
        with requests.get(get_doc_info_url, headers=headers, verify=False) as r:
            if r.status_code != requests.codes.OK:
                self.err = "资源获取失败"
                alert(
                    "百度文库资源获取失败",
                    status_code=r.status_code,
                    response=r.text,
                    user=UserSerializers(self.user).data,
                    url=self.url,
                )
                return

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
                                alert(
                                    "百度文库资源获取失败",
                                    status_code=r2.status_code,
                                    response=r2.text,
                                    user=UserSerializers(self.user).data,
                                    url=self.url,
                                )
                                return

                            resp = r2.json()
                            if resp["status"]["code"] != 0:
                                self.err = "资源获取失败"
                                alert(
                                    "百度文库资源获取失败",
                                    status_code=r2.status_code,
                                    response=r2.text,
                                    user=UserSerializers(self.user).data,
                                    url=self.url,
                                )
                                return

                            if resp["data"]["is_vip_free_doc"]:
                                point = settings.WENKU_VIP_FREE_DOC_POINT
                                wenku_type = "VIP免费文档"
                            else:
                                point = settings.WENKU_SHARE_DOC_POINT
                                wenku_type = "共享文档"

                        except Exception as e:
                            alert(
                                "百度文库资源获取失败",
                                status_code=r2.status_code,
                                response=r2.text,
                                user=UserSerializers(self.user).data,
                                url=self.url,
                                exception=e,
                            )
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
                alert(
                    "百度文库资源获取失败",
                    status_code=r2.status_code,
                    response=r2.text,
                    user=UserSerializers(self.user).data,
                    url=self.url,
                    exception=e,
                )
                self.err = "资源获取失败"

    def _download(self):
        api = f"{settings.DOWNHUB_SERVER}/parse/wenku"
        payload = {"url": self.url}
        headers = {"token": settings.DOWNHUB_TOKEN}
        with requests.post(api, json=payload, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                self.err = "下载失败"
                alert(
                    "百度文库下载失败",
                    status_code=r.status_code,
                    response=r.text,
                    url=self.url,
                    user=UserSerializers(self.user).data,
                )
                return

            try:
                download_url = r.json().get("data", None)
                if not download_url:
                    self.err = "下载失败"
                    alert(
                        "百度文库下载失败",
                        status_code=r.status_code,
                        response=r.text,
                        url=self.url,
                        user=UserSerializers(self.user).data,
                    )
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
                    alert(
                        "百度文库下载失败",
                        status_code=r.status_code,
                        response=r.text,
                        url=self.url,
                        user=UserSerializers(self.user).data,
                    )
                    return

                with requests.get(download_url, stream=True) as r2:
                    if r2.status_code != requests.codes.OK:
                        self.err = "下载失败"
                        alert(
                            "百度文库下载失败",
                            status_code=r2.status_code,
                            response=r2.text,
                            url=self.url,
                            user=UserSerializers(self.user).data,
                            download_url=download_url,
                        )
                        return

                    self.write_file(r2)

            except Exception as e:
                alert(
                    "百度文库下载失败",
                    url=self.url,
                    user=UserSerializers(self.user).data,
                    exception=e,
                )
                self.err = "下载失败"
