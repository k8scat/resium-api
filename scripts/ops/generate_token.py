# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/26

"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resium.settings.dev")
django.setup()

from downloader.utils import generate_jwt

if __name__ == "__main__":
    uid = "000000"
    token = generate_jwt(uid)
    print(token)
