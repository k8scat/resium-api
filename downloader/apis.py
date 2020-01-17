# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import datetime
import json
import logging
import string

import requests
from bs4 import BeautifulSoup
from django.shortcuts import redirect
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
from django.http import JsonResponse, HttpResponse, FileResponse, StreamingHttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import User, DownloadRecord, Order, Service, Csdnbot, Resource, ResourceTag
from downloader.serializers import UserSerializers, DownloadRecordSerializers, OrderSerializers, ServiceSerializers
from downloader.utils import ding, aliyun_oss_upload, aliyun_oss_check_file, aliyun_oss_sign_url


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
                # 设置token过期时间
                exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
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
        if User.objects.filter(email=email, is_active=True).count() != 0:
            return JsonResponse(dict(code=400, msg='邮箱已注册'))
        if User.objects.filter(invite_code=invited_code, is_active=True).count() != 1:
            return JsonResponse(dict(code=400, msg='邀请码无效'))

        encrypted_password = make_password(password)
        code = ''.join(random.sample(string.digits, 6))

        # 结合uuid和数据库生成唯一邀请码
        invite_code = ''.join(random.sample(string.digits, 6))
        while True:
            if User.objects.filter(invite_code=invite_code).count():
                invite_code = ''.join(random.sample(string.digits, 6))
                continue
            else:
                break
        user = User.objects.create(email=email, password=encrypted_password, invited_code=invited_code, code=code, invite_code=invite_code)

        activate_url = quote(settings.CSDNBOT_API + '/activate/?email=' + email + '&code=' + code, encoding='utf-8', safe=':/?=&')
        subject = '[CSDNBot] 用户注册'
        html_message = render_to_string('downloader/register.html', {'activate_url': activate_url})
        plain_message = strip_tags(html_message)
        from_email = f'CSDNBot <{settings.EMAIL_HOST_USER}>'
        try:
            send_mail(subject=subject,
                      message=plain_message,
                      from_email=from_email,
                      recipient_list=[email],
                      html_message=html_message,
                      fail_silently=False)
            return JsonResponse(dict(code=200, msg='注册成功，请前往邮箱激活账号'))
        except Exception as e:
            logging.error(e)
            user.delete()
            ding('注册激活邮件发送失败')
            return JsonResponse(dict(code=500, msg='注册失败'))

    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def activate(request):
    if request.method == 'GET':
        email = request.GET.get('email', None)
        code = request.GET.get('code', None)
        if email is None or code is None:
            return redirect(settings.CSDNBOT_UI + '/login?msg=错误的请求')

        if User.objects.filter(email=email, is_active=True).count():
            return redirect(settings.CSDNBOT_UI + '/login?msg=账号已激活')

        try:
            user = User.objects.get(email=email, code=code, is_active=False)
            user.is_active = True
            user.save()

            User.objects.filter(email=email, is_active=False).delete()
            return redirect(settings.CSDNBOT_UI + '/login?msg=激活成功')

        except User.DoesNotExist:
            return redirect(settings.CSDNBOT_UI + '/login?msg=账号不存在')

    else:
        return redirect(settings.CSDNBOT_UI + '/login?msg=错误的请求')


def download(request):
    if request.method == 'GET':
        resource_url = request.GET.get('resource_url', None)
        if resource_url is None:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        # 获取用户邮箱
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
            if user.valid_count <= 0:
                return JsonResponse(dict(code=403, msg='下载数已用完'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        # 这个今日资源下载数计算可能包含了以前下载过的资源，所以存在误差，偏大
        today_download_count = DownloadRecord.objects.filter(create_time__day=datetime.date.today().day, is_deleted=False).values('resource_url').distinct().count()
        logging.info(today_download_count)
        if today_download_count == 20:
            return JsonResponse(dict(code=403, msg='本站今日下载总数已达上限，请明日再来下载'))

        if not Csdnbot.objects.get(id=1).status:
            ding('系统还未恢复')
            return JsonResponse(dict(code=403, msg='本站下载服务正在维护中，将尽快恢复服务'))

        try:
            dr = DownloadRecord.objects.get(user=user, resource_url=resource_url, is_deleted=False)
            dr.update_time = timezone.now()
            dr.save()
        except DownloadRecord.DoesNotExist:
            # 判断用户是否有可用下载数
            # 更新用户的可用下载数和已用下载数
            user.valid_count -= 1
            user.used_count += 1
            user.save()
            # 保存下载记录
            DownloadRecord.objects.create(user=user, resource_url=resource_url)

        # 使用filter，防止存在多条资源记录时get出错
        resources = Resource.objects.filter(csdn_url=resource_url).all()
        # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
        if resources.count() and aliyun_oss_check_file(resources[0].key):
            download_url = aliyun_oss_sign_url(resources[0].key)
            logging.info(download_url)
            subject = '[CSDNBot] 资源下载'
            html_message = render_to_string('downloader/resource.html', {'download_url': download_url})
            plain_message = strip_tags(html_message)
            from_email = f'CSDNBot <{settings.EMAIL_HOST_USER}>'
            try:
                send_mail(subject=subject,
                          message=plain_message,
                          from_email=from_email,
                          recipient_list=[email],
                          html_message=html_message,
                          fail_silently=False)
                return JsonResponse(dict(code=200, msg='下载成功，资源链接已发送至您的注册邮箱！'))
            except Exception as e:
                logging.error(e)
                ding('资源链接邮件发送失败')
                Csdnbot.objects.filter(id=1).update(status=False)
                return JsonResponse(dict(code=500, msg='下载失败'))

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
        # 线上使用selenium server
        driver = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps, options=options)

        # 本地图形界面自动化测试
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

            # 访问资源地址
            driver.get(resource_url)

            # 点击VIP下载按钮
            el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "VIP下载"))
            )
            el.click()

            # 点击弹框中的VIP下载
            el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "(.//*[normalize-space(text()) and normalize-space(.)='为了良好体验，不建议使用迅雷下载'])[1]/following::a[1]"))
            )
            el.click()

            while True:
                files = os.listdir(sub_dir)
                if len(files) == 0 or files[0].endswith('.crdownload'):
                    logging.info('Downloading')
                    time.sleep(0.1)
                    continue
                else:
                    time.sleep(0.1)
                    logging.info('Download ok')
                    break

            # 下载完成后，文件夹下存在唯一的文件
            filename = files[0]
            # 生成文件的绝对路径
            file = os.path.join(sub_dir, filename)

            # 下载好文件后，直接保存资源信息并上传到阿里云的OSS上
            r = requests.get(resource_url)
            if r.status_code == 200:
                resource = None
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    title = soup.select('dl.resource_box_dl span.resource_title')[0].string
                    desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
                    size = os.path.getsize(file)
                    category = '-'.join([cat.string for cat in soup.select('div.csdn_dl_bread a')[1:3]])
                    # 存储在oss中的key
                    key = str(uuid.uuid1()) + '-' + filename
                    resource = Resource.objects.create(title=title, filename=filename, size=size, desc=desc,
                                                       csdn_url=resource_url, category=category, key=key)
                    tags = soup.select('div.resource_box_b label.resource_tags a')
                    resource_tags = []
                    for tag in tags:
                        resource_tags.append(ResourceTag(resource=resource, tag=tag.string))
                    ResourceTag.objects.bulk_create(resource_tags)

                    upload_success = aliyun_oss_upload(file, key)
                    if not upload_success:
                        resource.delete()
                        Csdnbot.objects.filter(id=1).update(status=False)
                        ding('阿里云OSS上传资源失败')
                        return JsonResponse(dict(code=500, msg='下载失败'))

                    download_url = aliyun_oss_sign_url(key)
                    logging.info(download_url)
                    subject = '[CSDNBot] 资源下载'
                    html_message = render_to_string('downloader/resource.html', {'download_url': download_url})
                    plain_message = strip_tags(html_message)
                    from_email = f'CSDNBot <{settings.EMAIL_HOST_USER}>'
                    try:
                        send_mail(subject=subject,
                                  message=plain_message,
                                  from_email=from_email,
                                  recipient_list=[email],
                                  html_message=html_message,
                                  fail_silently=False)
                        return JsonResponse(dict(code=200, msg='下载成功，资源链接已发送至您的注册邮箱！'))
                    except Exception as e:
                        logging.error(e)
                        ding('资源链接邮件发送失败')
                        Csdnbot.objects.filter(id=1).update(status=False)
                        return JsonResponse(dict(code=500, msg='下载失败'))

                except Exception as e:
                    if resource:
                        resource.delete()
                    logging.error(e)
                    Csdnbot.objects.filter(id=1).update(status=False)
                    ding('资源信息保存失败')
                    return JsonResponse(dict(code=500, msg='下载失败'))

        except Exception as e:
            logging.error(e)
            ding('下载失败 ' + str(e))
            Csdnbot.objects.filter(id=1).update(status=False)
            return JsonResponse(dict(code=500, msg='下载失败'))

        finally:
            driver.close()
    else:
        return HttpResponse('错误的请求')


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

                ding('收入+' + str(total_amount))
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

        download_records = DownloadRecord.objects.filter(user=user, is_deleted=False).all()
        return JsonResponse(dict(code=200, msg='获取下载记录成功', download_records=DownloadRecordSerializers(download_records, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def service(request):
    if request.method == 'GET':
        services = Service.objects.all()
        return JsonResponse(dict(code=200, msg='获取服务成功', services=ServiceSerializers(services, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def get_status(request):
    if request.method == 'GET':
        status = Csdnbot.objects.get(id=1).status
        return JsonResponse(dict(code=200, status=status))


def upload(request):
    if request.method == 'POST':
        pass


def test(request):
    aliyun_oss_upload('/Users/mac/workspace/CSDNBot/download/2d1fcd72-36c9-11ea-9742-a0999b0715d5/[www.java17.com]蓝桥杯java历年真题及答案整理(共129道题目及答案).doc', '[www.java17.com]蓝桥杯java历年真题及答案整理(共129道题目及答案).doc')
    return HttpResponse('test')


