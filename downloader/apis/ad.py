# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/6/17

"""
import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.models import MpSwiperAd
from downloader.serializers import MpSwiperAdSerializers


@api_view()
def list_mp_swiper_ads(request):
    mp_swiper_ads = MpSwiperAd.objects.all()
    return JsonResponse(dict(code=requests.codes.ok,
                             mp_swiper_ads=MpSwiperAdSerializers(mp_swiper_ads, many=True).data))
