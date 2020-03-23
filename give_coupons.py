# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/26

发放优惠券

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

from downloader.utils import *


if __name__ == '__main__':

    users = User.objects.filter(is_active=True).all()
    for user in users:
        if not create_coupon(user, '系统支付Bug'):
            print(user.email)
