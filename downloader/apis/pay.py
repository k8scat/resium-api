# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/9

"""
import datetime

from django.conf import settings
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view

from downloader.models import Order, User, Coupon
from downloader.utils import get_alipay, ding


@swagger_auto_schema(method='post')
@api_view(['POST'])
def alipay_notify(request):
    """
    支付宝回调接口
    """

    if request.method == 'POST':
        data = request.POST.dict()

        ali_pay = get_alipay()
        signature = data.pop("sign")
        # verification
        success = ali_pay.verify(data, signature)
        if success and data["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            app_id = data.get('app_id')
            if app_id != settings.ALIPAY_APP_ID:
                return HttpResponse('failure')

            out_trade_no = data.get('out_trade_no')
            total_amount = data.get('total_amount')
            try:
                o = Order.objects.get(out_trade_no=out_trade_no, total_amount=total_amount)
                o.paid_time = datetime.datetime.now()
                o.save()

                user = User.objects.get(id=o.user_id)
                user.valid_count += o.purchase_count
                user.save()

                ding('收入+' + str(total_amount))
            except Order.DoesNotExist:
                return HttpResponse('failure')
            return HttpResponse('success')
        return HttpResponse('failure')
