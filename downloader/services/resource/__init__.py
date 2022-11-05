import json
import logging
import os
import traceback
import uuid
from threading import Thread

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from lxml.etree import strip_tags

from downloader.models import DownloadAccount, STATUS_ENABLED
from downloader.utils import save_resource


class BaseResource:
    def __init__(self, url, user):
        self.account_type = ""

        self.url = url
        self.user = user
        self.unique_folder = None
        self.save_dir = None
        self.filepath = None
        self.filename = None
        self.resource = None
        self.account = None
        self.filename_uuid = None

        self.download_account = None
        self.download_account_config = None
        self.download_url = None
        self.err = None

    def _init_download_account(self):
        """初始下载账号"""
        if not self.account_type:
            return

        try:
            self.download_account = DownloadAccount.objects.filter(
                type=self.account_type, status=STATUS_ENABLED
            ).first()
            if self.download_account:
                self.download_account_config = json.loads(self.download_account.config)
        except Exception as e:
            logging.error(
                f"failed to init download account: {e}\n{traceback.format_exc()}"
            )
            self.err = "下载失败"

    def parse(self) -> None:
        raise NotImplementedError

    def _download(self) -> None:
        raise NotImplementedError

    def _init_download_dir(self):
        """
        调用download前必须调用_before_download

        :return:
        """

        # 生成资源存放的唯一子目录
        self.unique_folder = str(uuid.uuid1())
        self.save_dir = os.path.join(settings.DOWNLOAD_DIR, self.unique_folder)
        while True:
            if os.path.exists(self.save_dir):
                self.unique_folder = str(uuid.uuid1())
                self.save_dir = os.path.join(settings.DOWNLOAD_DIR, self.unique_folder)
            else:
                os.mkdir(self.save_dir)
                break

    def send_email(self):
        if not self.user.email:
            logging.warning("user email not found")
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
            logging.error(f"failed to send email: {e}\n{traceback.format_exc()}")

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

        self._init_download_dir()
        if self.err:
            return

        self._download()
        if self.err:
            return

        t1 = Thread(
            target=save_resource,
            args=(self.url, self.filename, self.filepath, self.resource, self.user),
            kwargs={"account_id": self.account.id if self.account else None},
        )
        t1.start()

        # 使用Nginx静态资源下载服务
        self.download_url = (
            f"{settings.NGINX_DOWNLOAD_URL}/{self.unique_folder}/{self.filename_uuid}"
        )

        t2 = Thread(target=self.send_email)
        t2.start()
