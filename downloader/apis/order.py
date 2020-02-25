# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import datetime
import logging
import uuid

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import Order, User, Coupon, Service
from downloader.serializers import OrderSerializers
from downloader.utils import get_alipay, ding


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


@auth
@api_view(['GET'])
def delete_order(request):
    if request.method == 'GET':
        order_id = request.GET.get('id', None)
        if order_id:
            try:
                order = Order.objects.get(id=order_id, is_deleted=False)
                order.is_deleted = True
                order.save()
                return JsonResponse(dict(code=200, msg='订单删除成功'))
            except Order.DoesNotExist:
                return JsonResponse(dict(code=400, msg='订单不存在'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def list_orders(request):
    """
    获取用户所有的订单

    需要认证
    """

    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        orders = Order.objects.order_by('-create_time').filter(user=user, is_deleted=False).all()
        return JsonResponse(dict(code=200, msg='获取购买记录成功', orders=OrderSerializers(orders, many=True).data))


@auth
@api_view(['POST'])
def create_order(request):
    """
    创建订单

    需要认证
    """

    if request.method == 'POST':
        total_amount = request.data.get('total_amount', None)
        purchase_count = request.data.get('purchase_count', None)
        code = request.data.get('code', None)

        c = None
        if code:
            try:
                c = Coupon.objects.get(code=code, total_amount=total_amount, purchase_count=purchase_count,
                                       is_used=False)
                c.is_used = True
                c.save()
            except Coupon.DoesNotExist:
                return JsonResponse(dict(code=404, msg='优惠券不存在'))
        else:
            if Service.objects.filter(total_amount=total_amount, purchase_count=purchase_count).count() == 0:
                return JsonResponse(dict(code=404, msg='服务不存在'))

        if total_amount is None or purchase_count is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        subject = '购买资源下载服务'

        ali_pay = get_alipay()
        # 生成唯一订单号
        out_trade_no = str(uuid.uuid1()).replace('-', '')

        order_string = ali_pay.api_alipay_trade_page_pay(
            # 商户订单号
            out_trade_no=out_trade_no,
            total_amount=total_amount,
            subject=subject,
            return_url=settings.CSDNBOT_UI
        )
        # 生成支付链接
        pay_url = settings.ALIPAY_WEB_BASE_URL + order_string

        # 获取当前用户
        email = request.session.get('email')
        user = User.objects.get(email=email)

        # 创建订单
        try:
            o = Order.objects.create(user=user, subject=subject, out_trade_no=out_trade_no, total_amount=total_amount,
                                     pay_url=pay_url, purchase_count=purchase_count, coupon=c)
            return JsonResponse(dict(code=200, msg='订单创建成功', order=OrderSerializers(o).data))
        except Exception as e:
            logging.info(e)
            return JsonResponse(dict(code=400, msg='订单创建失败'))
