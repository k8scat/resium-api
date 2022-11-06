import random

import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.models import Advert, MpSwiperAd
from downloader.serializers import AdvertSerializers, MpSwiperAdSerializers


@api_view()
def get_random_advert(request: Request):
    count = request.GET.get("count", None)
    if count:
        try:
            adverts = random.sample(list(Advert.objects.all()), int(count))
            return JsonResponse(
                dict(
                    code=requests.codes.ok,
                    adverts=AdvertSerializers(adverts, many=True).data,
                )
            )
        except ValueError:
            return JsonResponse(dict(code=requests.codes.server_error, msg="推广数据不足"))
    advert = random.choice(Advert.objects.all())
    return JsonResponse(
        dict(code=requests.codes.ok, advert=AdvertSerializers(advert).data)
    )


@api_view()
def list_mp_swiper_ads(request: Request):
    mp_swiper_ads = MpSwiperAd.objects.filter(is_ok=True).all()
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            mp_swiper_ads=MpSwiperAdSerializers(mp_swiper_ads, many=True).data,
        )
    )
