# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/9

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from django.contrib.auth.hashers import make_password
from downloader.models import User


if __name__ == '__main__':
    User.objects.create(email='hsowan.me@gmail.com', password=make_password('holdon7868'), invite_code='123456', valid_count=10000, used_count=0, is_active=True)
