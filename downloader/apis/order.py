# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import json
import logging
import uuid

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from wechatpy import WeChatPay

from downloader.decorators import auth
from downloader.models import Order, User, PointRecord
from downloader.serializers import OrderSerializers
from downloader.utils import get_alipay, ding, get_unique_str


@api_view(['POST'])
def alipay_notify(request):
    """
    支付宝回调接口
    """

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
            order = Order.objects.get(out_trade_no=out_trade_no, total_amount=total_amount)
            order.has_paid = True
            order.save()

            user = User.objects.get(id=order.user_id)
            user.point += order.point
            user.save()
            PointRecord(user=user, point=user.point,
                        add_point=order.point, comment='捐赠支持').save()

            ding(f'收入+{total_amount}',
                 uid=user.uid)
        except Order.DoesNotExist:
            return HttpResponse('failure')
        return HttpResponse('success')
    return HttpResponse('failure')


@auth
@api_view()
def delete_order(request):
    order_id = request.GET.get('id', None)
    if order_id:
        try:
            order = Order.objects.get(id=order_id, is_deleted=False)
            order.is_deleted = True
            order.save()
            return JsonResponse(dict(code=requests.codes.ok, msg='订单删除成功'))
        except Order.DoesNotExist:
            return JsonResponse(dict(code=requests.codes.not_found, msg='订单不存在'))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))


@auth
@api_view()
def list_orders(request):
    """
    获取用户所有的订单

    需要认证
    """

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='用户不存在'))

    orders = Order.objects.order_by('-create_time').filter(user=user, is_deleted=False).all()
    return JsonResponse(dict(code=requests.codes.ok, orders=OrderSerializers(orders, many=True).data))


def mp_pay_notify(request):
    logging.info('*********************************7777')
    logging.info(request.body)
    return HttpResponse('')


@auth
@api_view(['POST'])
def mp_pay(request):
    """
    微信支付

    创建订单

    :param request:
    :return:
    """

    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)

    code = request.data.get('code', None)
    subject = request.data.get('subject', None)
    total_amount = request.data.get('total_amount', None)
    point = request.data.get('point', None)
    if not code or not total_amount or not point or not subject:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))
    total_amount = int(total_amount * 100)  # 单位分

    params = {
        'appid': settings.WX_PAY_MP_APP_ID,
        'secret': settings.WX_PAY_MP_APP_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    with requests.get('https://api.weixin.qq.com/sns/jscode2session', params=params) as r:
        if r.status_code == requests.codes.OK:
            data = r.json()
            logging.info(data)
            if data.get('errcode', 0) == 0:  # 没有errcode或者errcode为0时表示请求成功
                # 生成唯一订单号
                out_trade_no = get_unique_str()

                we_chat_pay = WeChatPay(
                    appid=settings.WX_PAY_MP_APP_ID,
                    mch_key=settings.WX_PAY_MCH_KEY,
                    mch_cert=settings.WX_PAY_MCH_CERT,
                    sub_appid=settings.WX_PAY_SUB_APP_ID,
                    api_key=settings.WX_PAY_API_KEY,
                    mch_id=settings.WX_PAY_MCH_ID
                )
                logging.info(settings.WX_PAY_NOTIFY_URL)
                create_order_res = we_chat_pay.order.create(
                    trade_type='JSAPI',
                    body=subject,
                    total_fee=total_amount,
                    notify_url=settings.WX_PAY_NOTIFY_URL,
                    out_trade_no=out_trade_no,
                    user_id=data['openid']
                )
                logging.info(create_order_res)
                if create_order_res.get('return_code', None) == 'SUCCESS' and \
                        create_order_res.get('result_code', None) == 'SUCCESS':
                    # 创建内部系统的订单
                    Order(user=user, subject=subject,
                          out_trade_no=out_trade_no, total_amount=total_amount,
                          point=point).save()
                    # 再次签名
                    prepay_id = create_order_res.get('prepay_id')
                    nonce_str = create_order_res.get('nonce_str')
                    sign = we_chat_pay.jsapi.get_jsapi_signature(
                        prepay_id=prepay_id,
                        nonce_str=nonce_str
                    )
                    return JsonResponse(dict(code=requests.codes.ok, nonce_str=nonce_str,
                                             sign=sign, prepay_id=prepay_id))

                ding('[微信支付] 创建订单失败',
                     error=json.dumps(create_order_res),
                     need_email=True)
                return JsonResponse(dict(code=requests.codes.server_error, msg='订单创建失败'))

            else:
                ding('[微信支付] auth.code2Session接口请求成功，但返回结果错误',
                     error=r.text,
                     need_email=True)
                return JsonResponse(dict(code=requests.codes.server_error, msg='登录状态错误'))
        else:
            ding(f'[微信支付] auth.code2Session接口调用失败',
                 error=r.text,
                 need_email=True)
            return JsonResponse(dict(code=requests.codes.server_error, msg='登录状态错误'))


@auth
@api_view(['POST'])
def create_order(request):
    """
    支付宝

    创建订单
    """

    # 获取当前用户
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg='未认证'))

    subject = request.data.get('subject', None)
    total_amount = request.data.get('total_amount', None)
    point = request.data.get('point', None)

    if not total_amount or not point or not subject:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    ali_pay = get_alipay()
    # 生成唯一订单号
    out_trade_no = str(uuid.uuid1()).replace('-', '')

    order_string = ali_pay.api_alipay_trade_page_pay(
        # 商户订单号
        out_trade_no=out_trade_no,
        total_amount=total_amount,
        subject=subject,
        return_url=settings.FRONTEND_URL
    )
    # 生成支付链接
    pay_url = settings.ALIPAY_WEB_BASE_URL + order_string

    # 创建订单
    try:
        order = Order.objects.create(user=user, subject=subject,
                                     out_trade_no=out_trade_no, total_amount=total_amount,
                                     pay_url=pay_url, point=point)
        return JsonResponse(dict(code=requests.codes.ok, order=OrderSerializers(order).data))
    except Exception as e:
        logging.info(e)
        return JsonResponse(dict(code=requests.codes.server_error, msg='订单创建失败'))
