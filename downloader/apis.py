# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import datetime
import json
import logging
import string

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote

import alipay
import random

import jwt
import os
import time
import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponse, FileResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from urllib import parse

from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import User, DownloadRecord, Order, Service
from downloader.serializers import UserSerializers, DownloadRecordSerializers, OrderSerializers, ServiceSerializers

test_url = 'https://download.csdn.net/download/m0_37829784/11088464'


def login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception as e:
            logging.error(e)
            return JsonResponse(dict(code=400, msg='错误的请求'))

        email = data.get('email', None)
        password = data.get('password', None)
        if email is None or password is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        try:
            user = User.objects.get(email=email, is_active=True)
            if check_password(password, user.password):
                # 设置token过期时间: 1day
                exp = timezone.now() + datetime.timedelta(hours=1)
                payload = {
                    'exp': exp,
                    'sub': email
                }
                token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS512').decode()
                return JsonResponse(dict(code=200, msg="登录成功", token=token))
            else:
                return JsonResponse(dict(code=404, msg='邮箱或密码不正确'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='邮箱或密码不正确'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def get_user(request):
    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        return JsonResponse(dict(code=200, msg='获取用户信息成功', user=UserSerializers(user).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception as e:
            logging.error(e)
            return JsonResponse(dict(code=400, msg='错误的请求'))

        email = data.get('email', None)
        password = data.get('password', None)
        invited_code = data.get('invited_code', None)

        if email is None or password is None or invited_code is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        # 检查邮箱是否已注册以及邀请码是否有效
        if User.objects.filter(email=email, is_active=True).all().count() != 0:
            return JsonResponse(dict(code=400, msg='邮箱已注册'))
        if User.objects.filter(invite_code=invited_code, is_active=True).all().count() != 1:
            return JsonResponse(dict(code=400, msg='邀请码无效'))

        encrypted_password = make_password(password)
        code = ''.join(random.sample(string.digits, 6))

        # 结合uuid和数据库生成唯一邀请码
        invite_code = ''.join(random.sample(string.digits, 6))
        while True:
            if User.objects.filter(invite_code=invite_code).all().count():
                invite_code = ''.join(random.sample(string.digits, 6))
                continue
            else:
                break
        user = User.objects.create(email=email, password=encrypted_password, invited_code=invited_code, code=code, invite_code=invite_code)

        activate_url = quote(settings.CSDNBOT_UI + '/activate/?email=' + email + '&code=' + code, encoding='utf-8')
        subject = '[CSDNBot] 用户注册'
        html_message = render_to_string('downloader/register.html', {'activate_url': activate_url})
        plain_message = strip_tags(html_message)
        from_email = 'CSDNBot <admin@csdnbot.com>'
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=from_email,
                      recipient_list=[email],
                      html_message=html_message,
                      fail_silently=False)
            return JsonResponse(dict(code=200, msg='注册成功'))
        except Exception as e:
            logging.error(e)
            user.delete()
            return JsonResponse(dict(code=500, msg='注册失败，请重新注册'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def activate(request):
    if request.method == 'GET':
        email = request.GET.get('email', None)
        code = request.GET.get('code', None)
        if email is None or code is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        try:
            user = User.objects.get(email=email, code=code, is_active=False)
            user.is_active = True
            user.save()
            return JsonResponse(dict(code=200, msg='激活成功'))

        except User.DoesNotExist:
            return JsonResponse(dict(code=400, msg='无效的请求'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def download(request):
    if request.method == 'GET':
        resource_url = request.GET.get('resource_url', None)
        token = request.GET.get('token', None)
        if resource_url is None or token is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS512'])
        if payload.get('exp') < time.time():
            return JsonResponse(dict(code=401, msg='未认证'))

        # 更新用户的可用下载数和已用下载数
        email = payload.get('sub', None)
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        # 判断用户是否有可用下载数
        print(user.valid_count)
        if user.valid_count > 0:
            user.valid_count -= 1
            user.used_count += 1
            user.save()
        else:
            return JsonResponse(dict(code=400, msg='下载数已用完'))

        # 保存下载记录
        DownloadRecord(user=user, resource_url=resource_url).save()

        # 生成资源存放的唯一子目录
        uuid_str = str(uuid.uuid1())
        sub_dir = os.path.join(settings.DOWNLOAD_DIR, uuid_str)
        os.mkdir(sub_dir)

        options = webdriver.ChromeOptions()
        prefs = {
            "download.prompt_for_download": False,
            'download.default_directory': '/download/' + uuid_str,  # 下载目录
            "plugins.always_open_pdf_externally": True,
            'profile.default_content_settings.popups': 0,  # 设置为0，禁止弹出窗口
            'profile.default_content_setting_values.images': 2,  # 禁止图片加载
        }
        options.add_experimental_option('prefs', prefs)

        caps = DesiredCapabilities.CHROME
        driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps, options=options)
        # driver = webdriver.Chrome(options=options, desired_capabilities=caps)

        try:
            # 先请求，再添加cookies
            # selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
            driver.get('https://download.csdn.net')
            # 从文件中获取到cookies
            with open(settings.COOKIES_FILE, 'r', encoding='utf-8') as f:
                cookies = json.loads(f.read())
            for c in cookies:
                driver.add_cookie({'name': c['name'], 'value': c['value'], 'path': c['path'], 'domain': c['domain'],
                                   'secure': c['secure']})

            # 解析文件名
            parse_url = 'https://download.csdn.net/source/download?source_id=' + resource_url[
                                                                                 resource_url.rindex('/') + 1:]
            driver.get(parse_url)
            html = driver.page_source
            data = json.loads(html[html.index('{'):html.index('}') + 1])
            # 解析得到的url
            parsed_url = data.get('data')
            params = parse.parse_qs(parse.urlparse(parsed_url).query)
            # response-content-disposition
            rcd = params['response-content-disposition'][0]
            filename = parse.unquote(rcd[rcd.index('"') + 1:rcd.rindex('"')])
            logging.info(filename)

            driver.get(resource_url)

            el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "VIP下载"))
            )
            el.click()

            el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "(.//*[normalize-space(text()) and normalize-space(.)='为了良好体验，不建议使用迅雷下载'])[1]/following::a[1]"))
            )
            el.click()

            file = os.path.join(sub_dir, filename)

            while True:

                files = os.listdir(sub_dir)
                if len(files) == 0 or files[0].endswith('.crdownload'):
                    logging.info('Downloading')
                    time.sleep(0.2)
                    continue
                else:
                    time.sleep(0.2)

                    logging.info('Download ok')
                    f = open(file, 'rb')
                    response = FileResponse(f)
                    response['Content-Type'] = 'application/octet-stream'
                    encoded_filename = parse.quote(filename, safe=string.printable)
                    response['Content-Disposition'] = 'attachment;filename="' + encoded_filename + '"'
                    return response

        except Exception as e:
            logging.error(e)
            return JsonResponse(dict(code=500, msg='下载失败'))

        finally:
            driver.close()
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def get_alipay():
    """
    获取AliPay实例

    :return:
    """

    with open(settings.ALIPAY_APP_PRIVATE_KEY_FILE) as f:
        alipay_app_private_key_string = f.read()
    with open(settings.ALIPAY_PUBLIC_KEY_FILE) as f:
        alipay_public_key_string = f.read()

    return alipay.AliPay(
        appid=settings.ALIPAY_APP_ID,
        app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,  # the default notify path
        app_private_key_string=alipay_app_private_key_string,
        # alipay public key, do not use your own public key!
        alipay_public_key_string=alipay_public_key_string,
        sign_type="RSA2",  # RSA or RSA2
        debug=False  # False by default
    )


def order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception as e:
            logging.error(e)
            return JsonResponse(dict(code=400, msg='错误的请求'))

        total_amount = data.get('total_amount', None)
        purchase_count = data.get('purchase_count', None)
        if total_amount is None or purchase_count is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        subject = '购买CSDNBot服务'

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
        o = Order.objects.create(user=user, subject=subject, out_trade_no=out_trade_no, total_amount=total_amount, pay_url=pay_url, purchase_count=purchase_count)
        return JsonResponse(dict(code=200, msg='订单创建成功', order=OrderSerializers(o).data))
    elif request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        orders = Order.objects.filter(user=user).all()
        return JsonResponse(dict(code=200, msg='获取购买记录成功', orders=OrderSerializers(orders, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def alipay_notify(request):
    if request.method == 'POST':

        data = request.POST.dict()
        logging.info(data)

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
                o.paid_time = timezone.now()
                o.save()

                user = User.objects.get(id=o.user_id)
                user.valid_count += o.purchase_count
                user.save()
            except Order.DoesNotExist:
                return HttpResponse('failure')
            return HttpResponse('success')
        return HttpResponse('failure')


def reset_password(request):
    if request.method == 'POST':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        try:
            data = json.loads(request.body)
        except Exception as e:
            logging.error(e)
            return JsonResponse(dict(code=400, msg='错误的请求'))

        old_password = data.get('old_password', None)
        new_password = data.get('new_password', None)
        if old_password is None or new_password is None or old_password == new_password:
            return JsonResponse(dict(code=200, msg='错误的请求'))

        if check_password(old_password, user.password):
            user.password = make_password(new_password)
            user.save()
            return JsonResponse(dict(code=200, msg='密码修改成功'))
        else:
            return JsonResponse(dict(code=400, msg='旧密码不正确'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def download_record(request):
    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        download_records = DownloadRecord.objects.filter(user=user).all()
        return JsonResponse(dict(code=200, msg='获取下载记录成功', download_records=DownloadRecordSerializers(download_records, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def service(request):
    if request.method == 'GET':
        services = Service.objects.all()
        return JsonResponse(dict(code=200, msg='获取服务成功', services=ServiceSerializers(services, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def test(request):
    file = '/Users/mac/workspace/CSDNBot/download/7e08b4e8-32e0-11ea-9039-a0999b0715d5/Travel.rar'
    f = open(file, 'rb')
    response = FileResponse(f)
    response['Content-Type'] = 'application/octet-stream'
    encoded_filename = parse.quote('Travel.rar', safe=string.printable)
    response['Content-Disposition'] = 'attachment;filename="' + encoded_filename + '"'
    return response
