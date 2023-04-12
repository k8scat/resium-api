import datetime
import hashlib
import json
import logging
import re
import time
import uuid
from urllib.parse import quote, unquote

import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.decorators import api_view
from rest_framework.request import Request
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
from wechatpy.events import UnsubscribeEvent, SubscribeEvent
from wechatpy.messages import TextMessage
from wechatpy.replies import TextReply, EmptyReply

from downloader.decorators import auth
from downloader.models import (
    User,
    Order,
    DownloadRecord,
    Resource,
    ResourceComment,
    Article,
    CheckInRecord,
    QrCode,
    PointRecord,
)
from downloader.utils.rsa import RSAUtil
from downloader.serializers import UserSerializers, PointRecordSerializers
from downloader.services.user import get_user_from_session

# from downloader.utils import (
#     ding,
#     send_email,
#     generate_uid,
#     generate_jwt,
#     get_random_int,
#     get_random_str,
# )
from downloader.utils import rand, jwt
from downloader.utils.alert import alert
from downloader.utils.email import send_email
from downloader.utils.pagination import parse_pagination_args


@auth
@api_view()
def get_user(request):
    user = get_user_from_session(request)
    if not user:
        return JsonResponse(dict(code=requests.codes.forbidden, msg="user not found"))

    return JsonResponse(dict(code=requests.codes.ok, user=UserSerializers(user).data))


@api_view(["POST"])
def mp_login(request):
    """
    :param request:
    :return:
    """

    code = request.data.get("code", None)
    avatar_url = request.data.get("avatar_url", None)
    nickname = request.data.get("nickname", None)
    gender = request.data.get("gender", None)
    if not code or not avatar_url or not nickname:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    params = {
        "appid": settings.WX_MP_APP_ID,
        "secret": settings.WX_MP_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    with requests.get(
        "https://api.weixin.qq.com/sns/jscode2session", params=params
    ) as r:
        if r.status_code == requests.codes.OK:
            data = r.json()
            if data.get("errcode", 0) == 0:  # 没有errcode或者errcode为0时表示请求成功
                mp_openid = data["openid"]
                login_time = datetime.datetime.now()
                try:
                    user = User.objects.get(mp_openid=mp_openid)
                    user.login_time = login_time
                    user.avatar_url = avatar_url
                    user.nickname = nickname
                    user.gender = gender
                    user.save()
                except User.DoesNotExist:
                    uid = rand.gen_uid()
                    user = User.objects.create(
                        uid=uid,
                        mp_openid=mp_openid,
                        avatar_url=avatar_url,
                        nickname=nickname,
                        login_time=login_time,
                        can_download=True,
                    )

                token = jwt.gen_jwt(user.uid, expire_seconds=0)
                return JsonResponse(
                    dict(
                        code=requests.codes.ok,
                        token=token,
                        user=UserSerializers(user).data,
                    )
                )

            else:
                alert("小程序登录失败", status_code=r.status_code, response=r.text)
                return JsonResponse(dict(code=requests.codes.server_error, msg="登录失败"))

        else:
            alert("小程序登录失败", status_code=r.status_code, response=r.text)
            return JsonResponse(dict(code=requests.codes.server_error, msg="登录失败"))


@api_view(["POST"])
def save_qr_code(request):
    """
    保存二维码唯一标志

    :param request:
    :return:
    """

    cid = request.data.get("cid", None)
    code_type = request.data.get("t", None)
    if not cid or not code_type:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    QrCode(cid=cid, code_type=code_type).save()
    return JsonResponse(dict(code=requests.codes.ok, msg="ok"))


@auth
@api_view()
def scan_code(request):
    """
    用户使用小程序扫码登录

    :param request:
    :return:
    """

    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    code_type = request.GET.get("t", None)  # 扫码类型，分类登录和绑定已有账号
    cid = request.GET.get("cid", None)
    if not code_type or not cid:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        qr_code = QrCode.objects.get(
            cid=cid,
            code_type=code_type,
            has_scanned=False,
            create_time__lt=datetime.datetime.now()
            + datetime.timedelta(seconds=settings.QR_CODE_EXPIRE),
        )
        qr_code.has_scanned = True

        if code_type == "login":
            qr_code.uid = user.uid
            qr_code.save()
            return JsonResponse(dict(code=requests.codes.ok, msg="登录成功"))

        else:
            return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    except QrCode.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="二维码已失效"))


@api_view()
def check_scan(request):
    """
    检查用户是否扫描二维码并登陆

    Todo: 二维码过期

    :param request:
    :return:
    """

    code_type = request.GET.get("t", None)  # 扫码类型，分类登录和绑定已有账号
    cid = request.GET.get("cid", None)
    if not code_type or not cid:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        qr_code = QrCode.objects.get(cid=cid, code_type=code_type)
        if not qr_code.has_scanned:
            return JsonResponse(dict(code=4000, msg="等待扫码"))

        if code_type == "login":
            if not qr_code.uid:
                return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

            try:
                user = User.objects.get(uid=qr_code.uid)
                token = jwt.gen_jwt(user.uid)
                return JsonResponse(
                    dict(
                        code=requests.codes.ok,
                        token=token,
                        user=UserSerializers(user).data,
                        msg="登录成功",
                    )
                )
            except User.DoesNotExist:
                return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

        else:
            return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    except QrCode.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))


@auth
@api_view(["POST"])
def set_password(request):
    uid = request.session.get("uid")
    user = User.objects.get(uid=uid)

    password = request.data.get("password", "")
    if not re.match(r"^[a-zA-Z0-9]{6,24}$", password):
        return JsonResponse(
            dict(code=requests.codes.bad_request, msg="密码必须是6到24位字母或数字")
        )

    msg = "密码修改成功" if user.password else "密码设置成功"
    user.password = make_password(password)
    user.save()
    return JsonResponse(dict(code=requests.codes.ok, msg=msg))


@api_view(["POST"])
def request_reset_password(request: Request):
    uid_or_email = request.data.get("uid_or_email")
    if not uid_or_email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="用户ID或邮箱不能为空"))

    try:
        user: User = User.objects.get(Q(uid=uid_or_email) | Q(email=uid_or_email))

        rsa_util = RSAUtil(pubkey_file=settings.RSA_PUBKEY_FILE)
        payload = {
            "uid": user.uid,
            "password": rand.get_random_str(16),
            "expires": int(time.time()) + 600,
        }
        token = rsa_util.encrypt_by_public_key(json.dumps(payload))
        token_encoded = quote(token)
        reset_password_url = (
            f"{settings.API_BASE_URL}/reset_password?token={token_encoded}"
        )

        subject = "[源自下载] 重置密码"
        data = {"reset_password_url": reset_password_url}
        html_message = render_to_string("downloader/reset_password.html", data)
        plain_message = strip_tags(html_message)
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            return JsonResponse(dict(code=requests.codes.ok, msg="密码重置链接已发送至邮箱，请查收邮件！"))

        except Exception as e:
            alert("重置密码邮件发送失败", exception=e, email=user.email, uid=user.uid)
            return JsonResponse(
                dict(code=requests.codes.server_error, msg="重置密码邮件发送失败")
            )

    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="账号不存在"))


@api_view()
def reset_password(request: Request):
    token = request.GET.get("token")
    if not token:
        return HttpResponseNotFound()

    token_decoded = unquote(token)
    rsa_util = RSAUtil(privkey_file=settings.RSA_PRIVKEY_FILE)
    raw_data = rsa_util.decrypt_by_private_key(token_decoded)
    try:
        data: dict = json.loads(raw_data)
        uid = data.get("uid")
        password = data.get("password")
        if not uid or not password:
            return HttpResponse("无效的请求")
        expires = data.get("expires", 0)
        if time.time() > expires:
            return HttpResponse("链接已过期")

        try:
            user: User = User.objects.get(uid=uid)
            user.password = make_password(password)
            user.save()

            subject = "[源自下载] 密码重置成功"
            data = {"username": user.nickname, "password": password}
            html_message = render_to_string("downloader/new_password.html", data)
            plain_message = strip_tags(html_message)
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                return HttpResponse("密码已重置，新密码将通过邮件发送到你的邮箱，请注意查收！")

            except Exception as e:
                alert(
                    "新密码邮件发送失败",
                    exception=e,
                    uid=user.uid,
                    email=user.email,
                    content=plain_message,
                )
                return HttpResponse("系统未知错误，请联系管理员！")

        except User.DoesNotExist:
            return HttpResponse("无效的请求")

    except Exception as e:
        logging.error(f"failed to reset password: {e}, raw_data={raw_data}")
        return HttpResponse("无效的请求")


@api_view(["POST"])
def login(request: Request):
    uid_or_email = request.data.get("uid_or_email", None)
    password = request.data.get("password", None)
    gender = request.data.get("gender", None)  # 通过小程序登录获取用户性别
    if not uid_or_email or not password:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        user = User.objects.get(Q(uid=uid_or_email) | Q(email=uid_or_email))
        if not user.password:
            return JsonResponse(dict(code=requests.codes.bad_request, msg="未设置密码"))

        if check_password(password, user.password):
            user.gender = gender
            user.save()
            token = jwt.gen_jwt(user.uid, expire_seconds=0)
            return JsonResponse(
                dict(
                    code=requests.codes.ok, token=token, user=UserSerializers(user).data
                )
            )

        else:
            return JsonResponse(dict(code=requests.codes.bad_request, msg="用户ID或密码不正确"))

    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="用户不存在"))

    except Exception as e:
        logging.error(f"login failed: {e}")
        return JsonResponse(dict(code=requests.codes.server_error, msg="系统错误"))


@auth
@api_view(["POST"])
def request_email_code(request: Request):
    """
    请求设置邮箱，会向邮箱发送确认链接

    :param request:
    :return:
    """

    user = get_user_from_session(request)
    email = request.data.get("email", "")
    if not re.match(r".+@.+\..+", email):
        return JsonResponse(dict(code=requests.codes.bad_request, msg="邮箱格式有误"))

    if user.email == email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="新邮箱不能和当前邮箱相同"))
    if User.objects.filter(email=email).count() > 0:
        return JsonResponse(dict(code=requests.codes.forbidden, msg="邮箱已被绑定其他账号！"))

    code = rand.get_random_int()
    cache.set(code, email, timeout=settings.EMAIL_CODE_EXPIRES)
    subject = "[源自下载] 验证码"
    data = {"code": code, "username": user.nickname}
    html_message = render_to_string("downloader/email_code.html", data)
    plain_message = strip_tags(html_message)
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return JsonResponse(dict(code=requests.codes.ok, msg="发送成功"))

    except Exception as e:
        alert(
            "邮箱验证码发送失败",
            exception=e,
            uid=user.uid,
            email=user.email,
            email_content=plain_message,
        )
        return JsonResponse(dict(code=requests.codes.server_error, msg="验证码发送失败"))


@auth
@api_view(["POST"])
def set_email_with_code(request: Request):
    """
    通过验证码设置邮箱

    :param request:
    :return:
    """

    user = get_user_from_session(request)
    post_email = request.data.get("email", None)
    if not re.match(r".+@.+\..+", post_email):
        return JsonResponse(dict(code=requests.codes.bad_request, msg="邮箱格式有误"))

    code = request.data.get("code")
    if not code:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="验证码有误"))

    email = cache.get(code)
    if not email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="无效的验证码"))
    if email != post_email:
        return JsonResponse(
            dict(code=requests.codes.bad_request, msg="邮箱不一致，请重新获取验证码！")
        )
    if not email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="验证码有误"))
    if User.objects.filter(email=email).count() > 0:
        return JsonResponse(dict(code=requests.codes.forbidden, msg="邮箱已被绑定其他账号！"))

    user.email = email
    user.save()
    cache.delete(code)
    return JsonResponse(dict(code=requests.codes.ok, msg="邮箱设置成功"))


@auth
@api_view()
def list_point_records(request):
    user = get_user_from_session(request)

    page, per_page = parse_pagination_args(request)
    start = per_page * (page - 1)
    end = start + per_page
    point_records = (
        PointRecord.objects.filter(user=user, is_deleted=False)
        .order_by("-create_time")
        .all()[start:end]
    )
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            point_records=PointRecordSerializers(point_records, many=True).data,
        )
    )


@auth
@api_view()
def delete_point_record(request):
    point_record_id = request.GET.get("id", None)
    if not point_record_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        point_record = PointRecord.objects.get(id=point_record_id)
        point_record.is_deleted = True
        point_record.save()
        return JsonResponse(dict(code=requests.codes.ok, msg="删除成功"))

    except PointRecord.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="积分记录不存在"))
