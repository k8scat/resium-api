# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

"""

import os

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.prod')
django.setup()

from downloader.models import User


if __name__ == '__main__':
    users = User.objects.filter(used_count__gt=0).delete()
