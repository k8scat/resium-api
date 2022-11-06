import json

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.pay import dict_to_xml

from downloader.decorators import auth
from downloader.models import Order, User, PointRecord
from downloader.serializers import OrderSerializers, UserSerializers
from downloader.services.user import get_user_from_session
from downloader.utils import rand, wechat_pay
from downloader.utils.alert import alert


@auth
@api_view()
def delete_order(request):
    order_id = request.GET.get("id", None)
    if order_id:
        try:
            order = Order.objects.get(id=order_id, is_deleted=False)
            order.is_deleted = True
            order.save()
            return JsonResponse(dict(code=requests.codes.ok, msg="订单删除成功"))

        except Order.DoesNotExist:
            return JsonResponse(dict(code=requests.codes.not_found, msg="订单不存在"))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))


@auth
@api_view()
def list_orders(request):
    """
    获取用户所有的订单

    需要认证
    """

    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="用户不存在"))

    orders = (
        Order.objects.order_by("-create_time").filter(user=user, is_deleted=False).all()
    )
    return JsonResponse(
        dict(code=requests.codes.ok, orders=OrderSerializers(orders, many=True).data)
    )


def mp_pay_notify(request):
    """
    支付结果通知
    https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_7&index=8

    :param request:
    :return:
    """

    instance = wechat_pay.get_instance()
    try:
        payment_result = instance.parse_payment_result(request.body)  # sdk已经验证了签名
        return_code = "SUCCESS"
        return_msg = "OK"

        total_amount = payment_result.get("total_fee") / 100  # 单位元
        out_trade_no = payment_result.get("out_trade_no")
        try:
            order = Order.objects.get(
                out_trade_no=out_trade_no, total_amount=total_amount
            )
            order.has_paid = True
            order.save()

            order.user.point += order.point
            order.user.save()

            PointRecord(
                user=order.user,
                point=order.user.point,
                add_point=order.point,
                comment="捐赠支持",
            ).save()
            alert("新增收入", money=total_amount, user=UserSerializers(order.user).data)

        except Order.DoesNotExist:
            pass

    except InvalidSignatureException:
        alert("微信支付签名校验失败", error=request.body)
        return_code = "FAIL"
        return_msg = "签名失败"

    ret_data = dict_to_xml({"return_code": return_code, "return_msg": return_msg})
    return HttpResponse(ret_data, content_type="text/xml")


@auth
@api_view(["POST"])
def mp_pay(request: Request):
    """
    微信支付 创建订单

    :param request:
    :return:
    """

    user = get_user_from_session(request)

    code = request.data.get("code", None)
    subject = request.data.get("subject", None)
    total_amount = request.data.get("total_amount", None)
    point = request.data.get("point", None)
    if not code or not total_amount or not point or not subject:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    total_fee = int(total_amount * 100)  # 单位分
    params = {
        "appid": settings.WX_PAY_MP_APP_ID,
        "secret": settings.WX_PAY_MP_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    with requests.get(
        "https://api.weixin.qq.com/sns/jscode2session", params=params
    ) as r:
        if r.status_code == requests.codes.OK:
            data = r.json()
            if data.get("errcode", 0) == 0:  # 没有errcode或者errcode为0时表示请求成功
                # 生成唯一订单号
                out_trade_no = rand.uuid()
                instance = wechat_pay.get_instance()
                create_order_res = instance.order.create(
                    trade_type="JSAPI",
                    body=subject,
                    total_fee=total_fee,
                    notify_url=settings.WX_PAY_NOTIFY_URL,
                    out_trade_no=out_trade_no,
                    user_id=data["openid"],
                )
                if (
                    create_order_res.get("return_code", None) == "SUCCESS"
                    and create_order_res.get("result_code", None) == "SUCCESS"
                ):
                    # 创建内部系统的订单
                    Order(
                        user=user,
                        subject=subject,
                        out_trade_no=out_trade_no,
                        total_amount=total_amount,
                        point=point,
                    ).save()
                    # 再次签名
                    prepay_id = create_order_res.get("prepay_id")
                    return JsonResponse(
                        dict(
                            code=requests.codes.ok,
                            params=instance.jsapi.get_jsapi_params(prepay_id=prepay_id),
                        )
                    )

                alert(
                    "微信支付创建订单失败",
                    error=json.dumps(create_order_res),
                    user=UserSerializers(user).data,
                )
                return JsonResponse(
                    dict(code=requests.codes.server_error, msg="订单创建失败")
                )

            else:
                alert(
                    "[微信支付] auth.code2Session接口请求成功，但返回结果错误",
                    status_code=r.status_code,
                    response=r.text,
                    user=UserSerializers(user).data,
                )
                return JsonResponse(
                    dict(code=requests.codes.server_error, msg="登录状态错误")
                )

        else:
            alert(
                "[微信支付] auth.code2Session接口调用失败",
                status_code=r.status_code,
                response=r.text,
                user=UserSerializers(user).data,
            )
            return JsonResponse(dict(code=requests.codes.server_error, msg="登录状态错误"))
