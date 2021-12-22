import logging
import os
import uuid

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from lxml.etree import strip_tags

from downloader.utils import ding


class BaseResource:
    def __init__(self, url, user):
        self.url = url
        self.user = user
        self.unique_folder = None
        self.save_dir = None
        self.filepath = None
        self.filename = None
        self.resource = None
        self.account = None
        self.filename_uuid = None

    def _before_download(self):
        """
        调用download前必须调用_before_download

        :return:
        """

        logging.info(f'资源下载: {self.url}')

        # 生成资源存放的唯一子目录
        self.unique_folder = str(uuid.uuid1())
        self.save_dir = os.path.join(settings.DOWNLOAD_DIR, self.unique_folder)
        while True:
            if os.path.exists(self.save_dir):
                self.unique_folder = str(uuid.uuid1())
                self.save_dir = os.path.join(
                    settings.DOWNLOAD_DIR, self.unique_folder)
            else:
                os.mkdir(self.save_dir)
                break

    def send_email(self, url):
        subject = '[源自下载] 资源下载成功'
        html_message = render_to_string(
            'downloader/download_url.html', {'url': url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[self.user.email],
                      html_message=html_message,
                      fail_silently=False)
            return requests.codes.ok, url
        except Exception as e:
            ding('资源下载地址邮件发送失败',
                 error=e,
                 uid=self.user.uid,
                 resource_url=self.url,
                 download_account_id=self.account.id,
                 logger=logging.error,
                 need_email=True)
            return requests.codes.server_error, '邮件发送失败'

    def parse(self):
        pass

    def __download(self):
        pass

    def get_filepath(self):
        """
        返回文件路径

        :return:
        """

        pass

    def get_url(self, use_email=False):
        """
        返回下载链接

        :param use_email: 是否使用邮件
        :return:
        """

        pass
