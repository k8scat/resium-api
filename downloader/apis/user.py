# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/9

"""
import datetime
import hashlib
import logging
import random
import re
import uuid

import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
from wechatpy.events import UnsubscribeEvent, SubscribeEvent
from wechatpy.messages import TextMessage
from wechatpy.replies import TextReply, EmptyReply

from downloader.decorators import auth
from downloader.models import User, Order, DownloadRecord, Resource, ResourceComment, DwzRecord, Article, Coupon, \
    CheckInRecord, QrCode
from downloader.serializers import UserSerializers
from downloader.utils import ding, send_email, generate_uid, generate_jwt


@auth
@api_view()
def get_user(request):
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
        return JsonResponse(dict(code=200, user=UserSerializers(user).data))
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view(['GET', 'POST'])
def wx(request):
    """
    微信公众平台接口

    接入文档
    https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Access_Overview.html

    开源SDK
    https://github.com/jxtech/wechatpy

    Django 返回字符串使用 return HttpResponse('str')

    :param request:
    :return:
    """
    if request.method == 'GET':
        """
        接入微信公众平台开发
        https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Access_Overview.html

        请求参数
        signature	微信加密签名，signature结合了开发者填写的token参数和请求中的timestamp参数、nonce参数。
        timestamp	时间戳
        nonce	随机数
        echostr	随机字符串

        请求示例
        /wx/?signature=c047ea9c3b369811f237ef4145a0092b03e53149&echostr=4106217736181366575&timestamp=1580479503&nonce=14640658
        """

        signature = request.GET.get('signature', '')
        timestamp = request.GET.get('timestamp', '')
        nonce = request.GET.get('nonce', '')
        echostr = request.GET.get('echostr', '')

        # 1）将token、timestamp、nonce三个参数进行字典序排序
        param_list = [settings.WX_TOKEN, timestamp, nonce]
        param_list.sort()
        tmp_str = ''.join(param_list)
        # 2）将三个参数字符串拼接成一个字符串进行sha1加密
        sha1 = hashlib.sha1(tmp_str.encode('utf-8'))
        hashcode = sha1.hexdigest()
        # 3）开发者获得加密后的字符串可与signature对比，标识该请求来源于微信
        if hashcode == signature:
            return HttpResponse(echostr)
        return HttpResponse('')
    elif request.method == 'POST':
        """
        消息管理

        文本消息
        <xml>
          <ToUserName><![CDATA[toUser]]></ToUserName>
          <FromUserName><![CDATA[fromUser]]></FromUserName>
          <CreateTime>1348831860</CreateTime>
          <MsgType><![CDATA[text]]></MsgType>
          <Content><![CDATA[this is a test]]></Content>
          <MsgId>1234567890123456</MsgId>
        </xml>

        加密消息
        b'<xml>\n    <ToUserName><![CDATA[gh_7ad5c6e34b81]]></ToUserName>\n    <Encrypt><![CDATA[+fOxSz93orPUJk5rDoevsIz1Zdt33oEEkgmpDDT8WK8mmCP1t+aXJzXUdzMiIy/vaigbvMrUI+BaKXlUhBuU04PSj5NFOEpmHaTRvXW+Otv0vtCY01MIinahpeHox+5d4Uvyf1Wa/m1+O5UiyI05r1eTBQZfC1Hxw4/JceqaRPcB+YAs+oykwJmwlHWLwsAyRTS/AAN3fpOy0Bwf12PTEqogpj4I7Kg2kxS50zLkjsnlHAn/H+UXzE6FppZjv0+Dks09LtEo+Uo10pi02yxnfF7OBVN1wsW7eEZLXBK3HyW1vbQFXwhcfvxIINXNWgxDRV20cnUlBBuIjXT8XEwNDkSU3G+/S2m9qk3Gr12rJB9r1s64zM5u9UOlrOAerGokKHDoV7QjNslPDxqxgAxjcsQxLO/hCJjL7vUIqlb93PA=]]></Encrypt>\n</xml>\n'

        回复文本消息
        <xml>
          <ToUserName><![CDATA[toUser]]></ToUserName>
          <FromUserName><![CDATA[fromUser]]></FromUserName>
          <CreateTime>12345678</CreateTime>
          <MsgType><![CDATA[text]]></MsgType>
          <Content><![CDATA[你好]]></Content>
        </xml>

        示例请求
        POST /wx/?signature=78b016334f993e6701897e0dec278ea731af7d72&timestamp=1580552507&nonce=1302514634&openid=oc5rb00oVXaRUTRvvbIpCvDNSoFA&encrypt_type=aes&msg_signature=73ef0f95249e268641de2dc87761f234ca9d6db0

        路径参数
        signature
        timestamp
        nonce
        openid
        encrypt_type
        msg_signature

        :return xml
        """

        msg_signature = request.GET.get('msg_signature', '')
        timestamp = request.GET.get('timestamp', '')
        nonce = request.GET.get('nonce', '')

        xml_data = request.body

        crypto = WeChatCrypto(settings.WX_TOKEN, settings.WX_ENCODING_AES_KEY, settings.WX_APP_ID)
        try:
            decrypted_xml = crypto.decrypt_message(
                xml_data,
                msg_signature,
                timestamp,
                nonce
            )
        except Exception as e:
            logging.info(e)
            reply = EmptyReply()
            # 转换成 XML
            ret_xml = reply.render()
            # 加密
            encrypted_xml = crypto.encrypt_message(ret_xml, nonce, timestamp)
            return HttpResponse(encrypted_xml, content_type="text/xml")

        msg = parse_message(decrypted_xml)
        reply = EmptyReply()

        # 关注事件
        if isinstance(msg, SubscribeEvent):
            ding('公众号关注 +1')
            content = '你好，欢迎关注源自开发者！' \
                      '\n\n每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享' \
                      '\n\n在线资源下载平台：https://resium.cn'
            reply = TextReply(content=content, message=msg)

        # 取消关注事件
        elif isinstance(msg, UnsubscribeEvent):
            try:
                user = User.objects.get(wx_openid=msg.source)
                user.wx_openid = None
                user.save()
                ding(f'源自下载用户{user.uid}取消关注公众号')
            except User.DoesNotExist:
                ding('公众号关注 -1')

        # 文本消息
        elif isinstance(msg, TextMessage):
            msg_content = msg.content.strip()

            if re.match(r'^.+@.+\..+', msg_content):  # 发送迁移码
                try:
                    email = msg_content
                    user = User.objects.get(email=email)
                    code = str(uuid.uuid1()).replace('-', '')
                    user.code = code
                    user.save()
                    try:
                        send_email('[源自下载] 账号迁移', f'迁移码：{code}', email)
                        content = '迁移码已发送至您的邮箱，请注意查收！部分邮件服务商可能会将系统邮件当作垃圾邮件, 请注意检查！'
                    except Exception as e:
                        ding('迁移码邮件发送失败',
                             error=e,
                             used_account=email,
                             logger=logging.error)
                        content = '邮件发送失败，请重新尝试或联系管理员！'
                except User.DoesNotExist:
                    content = '账号不存在'
                reply = TextReply(content=content, message=msg)

            elif re.match(r'^\d{6}$', msg_content):  # 绑定公众号
                try:
                    user = User.objects.get(uid=msg_content)
                    if user.wx_openid:
                        content = f'该账号已被微信绑定'
                    else:
                        user.wx_openid = msg.source
                        user.save()
                        content = '账号绑定成功'
                except User.DoesNotExist:
                    content = '账号不存在'
                reply = TextReply(content=content, message=msg)

            elif msg_content == '签到':  # 签到
                try:
                    user = User.objects.get(wx_openid=msg.source)
                    if user.has_check_in_today:
                        content = '今日已签到'
                    else:
                        # 随机获取积分
                        points = [1, 2, 3]
                        point = random.choice(points)
                        # 保存签到记录
                        CheckInRecord(user=user, point=point).save()
                        # 更新用户积分
                        user.point += point
                        user.has_check_in_today = True
                        user.save()
                        today = timezone.now().day
                        today_check_in_count = CheckInRecord.objects.filter(create_time__day=today).count()
                        today_check_in_point = CheckInRecord.objects.filter(create_time__day=today).aggregate(nums=Sum('point'))
                        ding(f'{user.nickname}签到成功，获得{point}积分，今日签到人数已达{today_check_in_count}人，总共免费获取{today_check_in_point}积分',
                             uid=user.uid)
                        content = f'签到成功，获得{point}积分'
                except User.DoesNotExist:
                    content = '请先绑定账号'
                reply = TextReply(content=content, message=msg)

            elif re.match(r'^\d{6} *[a-z0-9]+$', msg_content):  # 账号迁移
                uid = msg_content.split(' ')[0]
                if re.match(r'^\d{6}$', uid):
                    code = msg_content.split(' ')[-1]
                    try:
                        new_user = User.objects.get(uid=uid)
                        try:
                            old_user = User.objects.get(code=code)
                            new_user.point += old_user.point
                            new_user.used_point += old_user.used_point
                            new_user.can_download = old_user.can_download or new_user.can_download
                            new_user.save()
                            Order.objects.filter(user=old_user).update(user=new_user)
                            DownloadRecord.objects.filter(user=old_user).update(user=new_user)
                            Resource.objects.filter(user=old_user).update(user=new_user)
                            ResourceComment.objects.filter(user=old_user).update(user=new_user)
                            DwzRecord.objects.filter(user=old_user).update(user=new_user)
                            Article.objects.filter(user=old_user).update(user=new_user)
                            Coupon.objects.filter(user=old_user).update(user=new_user)
                            CheckInRecord.objects.filter(user=old_user).update(user=new_user)

                            old_user.delete()
                            content = '账号迁移成功'
                        except User.DoesNotExist:
                            content = '旧账号不存在'
                    except User.DoesNotExist:
                        content = '新账号不存在'

                    reply = TextReply(content=content, message=msg)

        # 转换成 XML
        ret_xml = reply.render()
        # 加密
        encrypted_xml = crypto.encrypt_message(ret_xml, nonce, timestamp)
        return HttpResponse(encrypted_xml, content_type="text/xml")
    else:
        return HttpResponse('')


@api_view(['POST'])
def reset_has_check_in_today(request):
    token = request.data.get('token', None)
    if token == settings.ADMIN_TOKEN:
        User.objects.filter(wx_openid__isnull=False, has_check_in_today=True).update(has_check_in_today=False)

    return HttpResponse('')


@api_view(['POST'])
def mp_login(request):
    """
    code 和 session_key 必须存在一个

    :param request:
    :return:
    """

    code = request.data.get('code', None)
    avatar_url = request.data.get('avatar_url', None)
    nickname = request.data.get('nickname', None)
    if not code:
        return JsonResponse(dict(code=400, msg='错误的请求'))
    if not avatar_url or not nickname:
        return JsonResponse(dict(code=400, msg='未设置微信昵称或头像'))

    params = {
        'appid': settings.WX_MP_APP_ID,
        'secret': settings.WX_MP_APP_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    with requests.get('https://api.weixin.qq.com/sns/jscode2session', params=params) as r:
        if r.status_code == requests.codes.OK:
            data = r.json()
            if data.get('errcode', 0) == 0:  # 没有errcode或者errcode为0时表示请求成功
                mp_openid = data['openid']
                login_time = datetime.datetime.now()
                try:
                    user = User.objects.get(mp_openid=mp_openid)
                    user.login_time = login_time
                    user.avatar_url = avatar_url
                    user.nickname = nickname
                    user.save()
                except User.DoesNotExist:
                    uid = generate_uid()
                    user = User.objects.create(uid=uid, mp_openid=mp_openid,
                                               avatar_url=avatar_url, nickname=nickname,
                                               login_time=login_time)

                token = generate_jwt(user.uid, expire_seconds=0)
                return JsonResponse(dict(code=200, token=token, user=UserSerializers(user).data))

            else:
                ding('[小程序登录] auth.code2Session接口请求成功，但返回结果错误',
                     error=r.text)
                return JsonResponse(dict(code=500, msg='登录失败'))
        else:
            ding(f'auth.code2Session接口调用失败',
                 error=r.text)
            return JsonResponse(dict(code=500, msg='登录失败'))


@api_view(['POST'])
def save_qr_code(request):
    """
    保存二维码唯一标志

    :param request:
    :return:
    """

    cid = request.data.get('cid', None)
    code_type = request.data.get('t', None)
    if not cid or not code_type:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    QrCode(cid=cid, code_type=code_type).save()
    return JsonResponse(dict(code=200, msg='ok'))


@auth
@api_view()
def scan_code(request):
    """
    小程序扫码登录

    :param request:
    :return:
    """

    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    code_type = request.GET.get('t', None)  # 扫码类型，分类登录和绑定已有账号
    cid = request.GET.get('cid', None)
    if not code_type or not cid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        qr_code = QrCode.objects.get(cid=cid, code_type=code_type, has_scanned=False,
                                     create_time__lt=datetime.datetime.now() + datetime.timedelta(
                                         seconds=settings.QR_CODE_EXPIRE))
        qr_code.has_scanned = True

        if code_type == 'login':
            qr_code.uid = user.uid
            qr_code.save()
            return JsonResponse(dict(code=200, msg='确认登录'))

        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))

    except QrCode.DoesNotExist:
        return JsonResponse(dict(code=400, msg='二维码已失效'))


@api_view()
def check_scan(request):
    code_type = request.GET.get('t', None)  # 扫码类型，分类登录和绑定已有账号
    cid = request.GET.get('cid', None)
    if not code_type or not cid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        qr_code = QrCode.objects.get(cid=cid, code_type=code_type)
        if not qr_code.has_scanned:
            return JsonResponse(dict(code=4000, msg='等待扫码'))

        if code_type == 'login':
            if not qr_code.uid:
                return JsonResponse(dict(code=400, msg='错误的请求'))

            try:
                user = User.objects.get(uid=qr_code.uid)
                token = generate_jwt(user.uid)
                return JsonResponse(dict(code=200, token=token, user=UserSerializers(user).data, msg='登录成功'))
            except User.DoesNotExist:
                return JsonResponse(dict(code=400, msg='错误的请求'))

        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))

    except QrCode.DoesNotExist:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['POST'])
def set_password(request):
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    password = request.data.get('password', '')
    if not re.match(r'[a-zA-Z0-9]{6,24}', password):
        return JsonResponse(dict(code=400, msg='密码必须是6到24位字母或数字'))

    user.password = make_password(password)
    user.save()
    return JsonResponse(dict(code=200, msg='密码设置成功'))


@api_view(['POST'])
def login(request):
    uid = request.data.get('uid', None)
    password = request.data.get('password', None)
    if not uid or not password:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)
        if check_password(password, user.password):
            token = generate_jwt(uid)
            return JsonResponse(dict(code=200, token=token))
        else:
            return JsonResponse(dict(code=400, msg='ID或密码不正确'))

    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='ID不存在'))
