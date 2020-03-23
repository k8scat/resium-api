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
import string
from urllib.parse import quote

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from faker import Faker
from ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
from wechatpy.events import UnsubscribeEvent, SubscribeEvent
from wechatpy.messages import TextMessage
from wechatpy.replies import TextReply, EmptyReply

from downloader.decorators import auth
from downloader.models import User, Resource
from downloader.serializers import UserSerializers
from downloader.utils import ding, create_coupon, send_message, send_email, aliyun_oss_delete_file


@auth
@api_view(['POST'])
def change_nickname(request):
    if request.method == 'POST':
        user_id = request.data.get('user_id', None)
        nickname = request.data.get('nickname', None)
        if user_id and nickname:
            try:
                user = User.objects.get(id=user_id, is_active=True)
                user.nickname = nickname
                user.save()
                return JsonResponse(dict(code=200, msg='昵称修改成功', user=UserSerializers(user).data))
            except User.DoesNotExist:
                return JsonResponse(dict(code=400, msg='错误的请求'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def get_user(request):
    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
            return JsonResponse(dict(code=200, user=UserSerializers(user).data))
        except User.DoesNotExist:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view(['POST'])
def login(request):
    """
    用户登录
    """
    if request.method == 'POST':
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        if not email or not password:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        try:
            user = User.objects.get(email=email, is_active=True)
            if check_password(password, user.password):
                login_device = request.META.get('HTTP_USER_AGENT', None)
                # Fix: remote ip addr is always local ip
                # https://stackoverflow.com/questions/4581789/how-do-i-get-user-ip-address-in-django
                if 'HTTP_X_FORWARDED_FOR' in request.META:
                    login_ip = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0]
                else:
                    login_ip = request.META.get('REMOTE_ADDR')

                if login_device and login_ip:
                    user.login_device = login_device
                    user.login_ip = login_ip
                    user.login_time = datetime.datetime.now()
                    user.save()
                else:
                    return JsonResponse(dict(code=400, msg='登录失败'))
                # 设置token过期时间
                exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
                payload = {
                    'exp': exp,
                    'sub': email
                }
                token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS512').decode()
                return JsonResponse(dict(code=200, msg="登录成功", token=token, user=UserSerializers(user).data))
            return JsonResponse(dict(code=404, msg='邮箱或密码不正确'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='邮箱或密码不正确'))


@api_view(['POST'])
def register(request):
    """
    用户注册
    """
    if request.method == 'POST':
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        code = request.data.get('code', None)

        if not email or not password or not code:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        # 检查邮箱是否已注册以及注册码是否有效
        if User.objects.filter(email=email, is_active=True).count() != 0:
            return JsonResponse(dict(code=400, msg='邮箱已注册'))
        if code != settings.REGISTER_CODE:
            return JsonResponse(dict(code=400, msg='注册码无效'))

        encrypted_password = make_password(password)
        code = ''.join(random.sample(string.digits, 6))
        fake = Faker('zh_CN')
        nickname = fake.name()
        User(email=email, password=encrypted_password, code=code, nickname=nickname).save()

        activate_url = quote(settings.RESIUM_API + '/activate/?email=' + email + '&code=' + code, encoding='utf-8',
                             safe=':/?=&')
        subject = '[源自下载] 用户注册'
        html_message = render_to_string('downloader/register.html', {'activate_url': activate_url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[email],
                      html_message=html_message,
                      fail_silently=False)
            return JsonResponse(dict(code=200, msg='注册成功，请前往邮箱激活账号'))
        except Exception as e:
            if str(e).count('Mailbox not found or access denied'):
                return JsonResponse(dict(code=400, msg='邮箱不可用，请使用其他邮箱注册'))
            logging.error(f'注册激活邮件发送失败: {str(e)}, 注册用户: {email}')
            ding(f'注册激活邮件发送失败: {str(e)}, 注册用户: {email}')
            return JsonResponse(dict(code=500, msg='激活邮件发送失败，请尝试使用其他邮箱注册'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


@api_view(['GET'])
def activate(request):
    """
    账号激活
    """

    if request.method == 'GET':
        email = request.GET.get('email', None)
        code = request.GET.get('code', None)
        if email is None or code is None:
            return redirect(settings.RESIUM_UI + '/login?msg=错误的请求')

        if User.objects.filter(email=email, is_active=True).count():
            return redirect(settings.RESIUM_UI + '/login?msg=账号已激活')

        try:
            user = User.objects.get(email=email, code=code, is_active=False)
            user.is_active = True
            user.save()

            # 优惠券
            if not create_coupon(user, '新用户注册'):
                return JsonResponse(dict(code=500, msg='注册失败'))

            User.objects.filter(email=email, is_active=False).delete()
            return redirect(settings.RESIUM_UI + '/login?msg=激活成功')

        except User.DoesNotExist:
            return redirect(settings.RESIUM_UI + '/login?msg=账号不存在')

    else:
        return redirect(settings.RESIUM_UI + '/login?msg=错误的请求')


@ratelimit(key='ip', rate='5/m', block=True)
@api_view(['GET'])
def send_forget_password_email(request):
    """
    发送重置密码的邮件
    """

    if request.method == 'GET':
        email = request.GET.get('email', None)
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        try:
            code = ''.join(random.sample(string.digits, 6))
            password = ''.join(random.sample(string.digits + string.ascii_letters, 16))
            encrypted_password = make_password(password)
            reset_password_url = quote(settings.RESIUM_API + '/forget_password/?token=' + encrypted_password + '&email=' + email + '&code=' + code,
                                       encoding='utf-8',
                                       safe=':/?=&')
            subject = '[源自下载] 密码重置'
            html_message = render_to_string('downloader/forget_password.html',
                                            {'reset_password_url': reset_password_url, 'password': password})
            plain_message = strip_tags(html_message)
            try:
                send_mail(subject=subject,
                          message=plain_message,
                          from_email=settings.DEFAULT_FROM_EMAIL,
                          recipient_list=[email],
                          html_message=html_message,
                          fail_silently=False)
                user.temp_password = encrypted_password
                user.code = code
                user.save()
                return JsonResponse(dict(code=200, msg='发送成功，请前往邮箱重置密码'))
            except Exception as e:
                logging.error(e)
                ding('密码重置邮件发送失败 ' + str(e))
                return JsonResponse(dict(code=500, msg='发送失败'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))


@ratelimit(key='ip', rate='5/m', block=True)
@api_view(['GET'])
def forget_password(request):
    """
    忘记密码: 确认重置密码

    :param request:
    :return:
    """

    if request.method == 'GET':
        email = request.GET.get('email', '')
        code = request.GET.get('code', '')
        temp_password = request.GET.get('token', '')
        if email and code and temp_password:
            try:
                user = User.objects.get(email=email, code=code, is_active=True, temp_password=temp_password)
                user.password = temp_password
                user.temp_password = None
                user.save()
                return redirect(settings.RESIUM_UI + '/login?msg=密码重置成功')
            except User.DoesNotExist:
                return redirect(settings.RESIUM_UI + '/login?msg=错误的请求')
        else:
            return redirect(settings.RESIUM_UI + '/login?msg=错误的请求')

    else:
        return redirect(settings.RESIUM_UI + '/login?msg=错误的请求')


@auth
@api_view(['POST'])
def reset_password(request):
    """
    修改密码
    """
    if request.method == 'POST':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        old_password = request.data.get('old_password', None)
        new_password = request.data.get('new_password', None)
        if not old_password or not new_password:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        if old_password == new_password:
            return JsonResponse(dict(code=400, msg='新密码不能和旧密码相同'))

        if check_password(old_password, user.password):
            user.password = make_password(new_password)
            user.save()
            return JsonResponse(dict(code=200, msg='密码修改成功'))
        return JsonResponse(dict(code=400, msg='旧密码不正确'))
    return JsonResponse(dict(code=400, msg='错误的请求'))


@ratelimit(key='ip', rate='3/h', block=settings.RATELIMIT_BLOCK)
@ratelimit(key='ip', rate='1/m', block=settings.RATELIMIT_BLOCK)
@auth
@api_view(['POST'])
def send_phone_code(request):
    if request.method == 'POST':
        # 目前只有绑定手机时会用到短信
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
            if user.phone:
                return JsonResponse(dict(code=400, msg='错误的请求'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        phone = request.data.get('phone', '')
        if not re.match(r'^1[3456789]\d{9}$', phone):
            return JsonResponse(dict(code=400, msg='手机号有误'))

        # Todo: 这时不应该计入请求次数
        if User.objects.filter(phone=phone, is_active=True).count() > 0:
            return JsonResponse(dict(code=400, msg='该手机号已绑定其他账号'))

        code = ''.join(random.sample(string.digits, 6))
        if send_message(phone, code):
            cache.set(phone, code, timeout=settings.PHONE_CODE_EXPIRE)
            return JsonResponse(dict(code=200, msg='验证码发送成功'))
        return JsonResponse(dict(code=500, msg='验证码发送失败'))


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
            content = '你好，欢迎关注源自下载！' \
                      '\n\n每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享'
            reply = TextReply(content=content, message=msg)

        # 取消关注事件
        elif isinstance(msg, UnsubscribeEvent):
            ding('公众号关注 -1')

        # 文本消息
        elif isinstance(msg, TextMessage):
            content = msg.content.strip()
            if re.match(r'^(r_audit: )\d+ (-)?\d( .+)?$', msg.content):
                # r_audit: 123 1 message
                content = content.split(' ')
                resource_id = int(content[1])
                is_audited = int(content[2])
                email_content = None
                if len(content) == 4:
                    email_content = content[3]
                try:
                    resource = Resource.objects.get(id=resource_id)
                    resource.is_audited = is_audited
                    resource.save()

                    # 发送邮件通知
                    subject = '[源自下载] 资源审核结果通知'
                    if is_audited == 1:
                        email_content = f'您上传的资源({resource.title})已经审核通过。'
                    elif is_audited == -1:
                        email_content = email_content if email_content else f'您上传的资源({resource.title})审核未通过。'
                    if email_content:
                        send_email(subject, email_content, resource.user.email)

                    content = '资源更新成功'
                except Resource.DoesNotExist:
                    content = '资源不存在'
                reply = TextReply(content=content, message=msg)
            elif re.match(r'^(r_del: ).+$', msg.content):
                resource_id = int(content.split('r_del: ')[1])
                try:
                    resource = Resource.objects.get(id=resource_id)
                    resource.delete()
                    aliyun_oss_delete_file(resource.key)
                    content = f'资源删除成功: {resource.key}'
                except Resource.DoesNotExist:
                    content = '资源不存在'
                reply = TextReply(content=content, message=msg)

        # 转换成 XML
        ret_xml = reply.render()
        # 加密
        encrypted_xml = crypto.encrypt_message(ret_xml, nonce, timestamp)
        return HttpResponse(encrypted_xml, content_type="text/xml")
    else:
        return HttpResponse('')


@auth
@api_view(['POST'])
def bind_phone(request):
    if request.method == 'POST':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
            if user.phone:
                return JsonResponse(dict(code=400, msg='该账号已绑定手机号'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        phone = request.data.get('phone', None)
        code = request.data.get('code', None)
        cache_code = cache.get(phone)
        if code != cache_code:
            return JsonResponse(dict(code=400, msg='验证码错误'))

        cache.delete(phone)
        user.phone = phone
        user.save()
        return JsonResponse(dict(code=200, msg='手机号绑定成功', user=UserSerializers(user).data))
