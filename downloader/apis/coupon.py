# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import User, Coupon
from downloader.serializers import CouponSerializers


@auth
@api_view(['GET'])
def list_coupons(request):
    """
    获取用户所有的优惠券

    需要认证
    """
    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))
        coupons = Coupon.objects.filter(user=user).all()
        return JsonResponse(dict(code=200, coupons=CouponSerializers(coupons, many=True).data))
