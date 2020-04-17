# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

手动处理数据

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

from downloader.models import User
from downloader.utils import *


if __name__ == '__main__':
    users = User.objects.filter(email__isnull=False)
    print(len(users))
    for user in users:
        code = str(uuid.uuid1()).replace('-', '')
        try:
            send_email('邮箱验证码', code, user.email)
            user.code = code
            user.save()
        except Exception as e:
            ding('发送失败',
                 error=e,
                 used_account=user.email)









