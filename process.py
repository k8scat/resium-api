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

from django.core.cache import cache
from django.db.models import Sum


from django.utils import timezone

from downloader.models import User, Order, CheckInRecord
from downloader.utils import *


if __name__ == '__main__':
    for resource in Resource.objects.filter(url__isnull=False).all():
        if re.match(settings.PATTERN_WENKU, resource.url):
            print(resource.url)
            # if resource.url.count('?') > 0:
            #     resource.url = resource.url.split('?')[0]
            # if resource.url.count('.html') == 0:
            #     if resource.url.count('.htm') == 1:
            #         resource.url = resource.url + 'l'
            #     else:
            #         resource.url = resource.url + '.html'
            #
            # resource.save()





