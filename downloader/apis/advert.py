# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/17

"""
import random

import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import Advert
from downloader.serializers import AdvertSerializers


@api_view()
def get_random_advert(request):
    count = request.GET.get('count', None)
    if count:
        try:
            adverts = random.sample(list(Advert.objects.all()), int(count))
            return JsonResponse(dict(code=requests.codes.ok, adverts=AdvertSerializers(adverts, many=True).data))
        except ValueError:
            return JsonResponse(dict(code=requests.codes.server_error, msg='推广数据不足'))
    advert = random.choice(Advert.objects.all())
    return JsonResponse(dict(code=requests.codes.ok, advert=AdvertSerializers(advert).data))
