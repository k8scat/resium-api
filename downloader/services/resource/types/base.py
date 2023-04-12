import json
import logging
import os
from threading import Thread
from typing import Dict

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from lxml.etree import strip_tags

from downloader.models import (
    DownloadAccount,
    DOWNLOAD_ACCOUNT_STATUS_ENABLED,
    User,
    PointRecord,
    Resource,
    DownloadRecord,
)
from downloader.serializers import UserSerializers, ResourceSerializers
from downloader.utils import file, aliyun_oss, rand
from downloader.utils.alert import alert


class BaseResource:
    def __init__(self, url: str, user: User):
        self.download_account_type: int | None = None

        self.url: str = url
        self.user: User = user

        self.file_key: str = ""
        self.filepath: str = ""
        self.filename: str = ""
        self.resource: Dict | None = None

        self.download_account: DownloadAccount | None = None
        self.download_account_config: Dict | None = None
        self.download_url: str = ""
        self.err: str | Dict | None = None

    def type(self) -> str:
        raise NotImplementedError

    @staticmethod
    def is_valid_url(url: str) -> bool:
        raise NotImplementedError

    def _init_download_account(self):
        """初始下载账号"""
        if not self.download_account_type:
            return

        try:
            self.download_account = DownloadAccount.objects.filter(
                type=self.download_account_type, status=DOWNLOAD_ACCOUNT_STATUS_ENABLED
            ).first()
            if not self.download_account:
                self.err = "下载失败"
                alert(
                    "下载账号不存在",
                    user=UserSerializers(self.user).data,
                    url=self.url,
                )
                return

            self.download_account_config = json.loads(self.download_account.config)

        except Exception as e:
            self.err = "下载失败"
            alert(
                "下载账号初始化失败",
                user=UserSerializers(self.user).data,
                url=self.url,
                exception=e,
            )

    def parse(self) -> None:
        raise NotImplementedError

    def _download(self) -> None:
        raise NotImplementedError

    def send_email(self):
        if not self.user.email:
            logging.warning(f"user email not found: {self.user.uid}")
            return

        subject = "[源自下载] 资源下载成功"
        html_message = render_to_string(
            "downloader/download_url.html", {"url": self.download_url}
        )
        plain_message = strip_tags(html_message)
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            alert(
                "资源下载邮件发送失败",
                exception=e,
                user=UserSerializers(self.user).data,
                url=self.url,
            )

    def _update_user(self):
        point = self.resource["point"]
        self.user.point -= point
        self.user.used_point += point
        self.user.save()

    def _add_download_record(self):
        PointRecord.objects.create(
            user=self.user,
            used_point=self.resource["point"],
            point=self.user.point,
            comment="下载资源",
            url=self.url,
        )

    def download(self) -> None:
        self.parse()
        if self.err:
            return
        if self.user.point < self.resource.get("point", 0):
            self.err = {"code": 5000, "msg": "积分不足，请进行捐赠支持。"}
            return

        self._init_download_account()
        if self.err:
            return

        self._add_download_record()
        self._update_user()

        self._download()
        if self.err:
            return

        t1 = Thread(target=self.save_resource)
        t1.start()

        # 使用Nginx静态资源下载服务
        self.download_url = f"{settings.NGINX_DOWNLOAD_URL}/{self.file_key}"
        t2 = Thread(target=self.send_email)
        t2.start()

    def write_file(self, resp: requests.Response):
        if not self.filename:
            self.err = "下载失败"
            alert("文件名获取失败", user=UserSerializers(self.user).data, url=self.url)
            return

        ext = os.path.splitext(self.filename)[1]
        self.file_key = rand.uuid() + ext
        self.filepath = os.path.join(settings.DOWNLOAD_DIR, self.file_key)
        with open(self.filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def save_resource(self):
        res = None
        try:
            with open(self.filepath, "rb") as f:
                file_md5 = file.md5(f)

            # 资源文件大小
            size = os.path.getsize(self.filepath)
            # django的CharField可以直接保存list，会自动转成str
            res = Resource.objects.create(
                title=self.resource.get("title", ""),
                filename=self.filename,
                size=size,
                url=self.url,
                key=self.file_key,
                tags=settings.TAG_SEP.join(self.resource.get("tags", [])),
                file_md5=file_md5,
                desc=self.resource.get("desc", ""),
                user=self.user,
            )
            DownloadRecord.objects.create(
                user=self.user,
                resource=res,
                used_point=self.resource.get("point", 0),
            )

            aliyun_oss.upload(self.filepath, self.file_key)

        except Exception as e:
            alert(
                "资源保存失败",
                url=self.url,
                user=UserSerializers(self.user).data,
                resource=self.resource,
                exception=e,
                res_db=ResourceSerializers(res).data if res else None,
            )
