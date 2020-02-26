# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/17

手动上传资源

"""

import os

import django
import uuid

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from downloader.models import Resource, User
from downloader.utils import get_file_md5

if __name__ == '__main__':

    filepath = '/Users/mac/Downloads/MODBUS软件开发实战指南.pdf'
    title = 'MODBUS软件开发实战指南.pdf'
    tags = settings.TAG_SEP.join(['MODBUS', '软件开发实战指南', '杨更更', '清华大学出版社'])
    desc = 'MODBUS软件开发实战指南.pdf'
    category = '-'.join(['电子书'])

    filename = filepath.split('/')[-1]
    size = os.path.getsize(filepath)
    with open(filepath, 'rb') as f:
        file_md5 = get_file_md5(f)
    if Resource.objects.filter(file_md5=file_md5).count():
        print('资源已存在')

    user = User.objects.get(email='17770040362@163.com', is_active=True)

    key = f'{str(uuid.uuid1())}-{filename}'
    print(key)
    Resource(title=title, desc=desc, tags=tags,
             category=category, filename=filename, size=size,
             is_audited=False, key=key, user=user, file_md5=file_md5,
             download_count=0).save()
