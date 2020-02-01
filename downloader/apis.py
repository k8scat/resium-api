# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import datetime
import hashlib
import json
import logging
import string
from threading import Thread
from urllib import parse

import requests
import xmltodict
from bs4 import BeautifulSoup
from django.db.models import Q
from django.shortcuts import redirect
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote

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
from django.utils.html import strip_tags
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

from selenium.webdriver.support.wait import WebDriverWait
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
from wechatpy.events import SubscribeEvent
from wechatpy.exceptions import InvalidAppIdException, InvalidSignatureException
from wechatpy.replies import TextReply, EmptyReply

from downloader.models import User, DownloadRecord, Order, Service, Csdnbot, Resource, Coupon
from downloader.serializers import UserSerializers, DownloadRecordSerializers, OrderSerializers, ServiceSerializers, \
    ResourceSerializers, CouponSerializers
from downloader.utils import ding, aliyun_oss_upload, aliyun_oss_check_file, aliyun_oss_get_file, csdn_auto_login, \
    get_alipay


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
        user = User.objects.create(email=email, password=encrypted_password, invited_code=invited_code, code=code,
                                   invite_code=invite_code)

        activate_url = quote(settings.CSDNBOT_API + '/activate/?email=' + email + '&code=' + code, encoding='utf-8',
                             safe=':/?=&')
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

            # 优惠券
            expire_time = datetime.datetime.now() + datetime.timedelta(days=7)
            comment = '新用户注册'
            code = str(uuid.uuid1()).replace('-', '')
            Coupon(user=user, total_amount=0.8, purchase_count=1, expire_time=expire_time, comment=comment,
                   code=code).save()

            User.objects.filter(email=email, is_active=False).delete()
            return redirect(settings.CSDNBOT_UI + '/login?msg=激活成功')

        except User.DoesNotExist:
            return redirect(settings.CSDNBOT_UI + '/login?msg=账号不存在')

    else:
        return redirect(settings.CSDNBOT_UI + '/login?msg=错误的请求')


def download(request):
    if request.method == 'GET':
        resource_url = request.GET.get('resource_url', None)
        token = request.GET.get('token', None)
        if not resource_url or not token:
            return HttpResponse('错误的请求')

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS512'])
        except Exception as e:
            logging.info(e)
            return HttpResponse('未认证')

        email = payload.get('sub', None)
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return HttpResponse('未认证')

        if not Csdnbot.objects.get(id=1).status:
            ding('系统还未恢复')
            return HttpResponse('本站下载服务正在维护中，将尽快恢复服务')

        def recover(u_: User, dr_: DownloadRecord = None):
            Csdnbot.objects.filter(id=1).update(status=False)
            u_.valid_count += 1
            u_.used_count -= 1
            u_.save()
            if dr_:
                dr_.is_deleted = True
                dr_.save()

        def get_driver():
            """
            获取driver

            :return: WebDriver
            """
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
            driver_ = webdriver.Remote(command_executor=settings.SELENIUM_SERVER, desired_capabilities=caps,
                                       options=options)

            # 本地图形界面自动化测试
            # driver_ = webdriver.Chrome(options=options)
            return driver_

        def add_cookie(driver_, cookies_file):
            """
            给driver添加cookies

            :param driver_:
            :param cookies_file:
            :return:
            """

            # 从文件中获取到cookies
            with open(cookies_file, 'r', encoding='utf-8') as f_:
                cookies_ = json.loads(f_.read())
            for cookie_ in cookies_:
                if 'expiry' in cookie_:
                    del cookie_['expiry']
                driver_.add_cookie(cookie_)

        def check_download(dir_):
            """
            判断文件是否下载完成

            :param dir_:
            :return:
            """
            while True:
                files = os.listdir(dir_)
                if len(files) == 0 or files[0].endswith('.crdownload'):
                    logging.info('Downloading')
                    time.sleep(0.1)
                    continue
                else:
                    time.sleep(0.1)
                    logging.info('Download ok')
                    break

            # 下载完成后，文件夹下存在唯一的文件
            filename_ = files[0]
            # 生成文件的绝对路径
            filepath_ = os.path.join(sub_dir, filename_)

            return filepath_, filename_

        def check_oss(resource_url_):
            """
            检查oss是否已存储资源

            :return: Resource
            """

            try:
                r_ = Resource.objects.get(url=resource_url_)
                # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
                # 如果oss上没有存储资源，则将resource删除
                if not aliyun_oss_check_file(r_.key):
                    r_.delete()
                    r_ = None
                return r_
            except Resource.DoesNotExist:
                return None

        dr = None
        try:
            # 判断用户是否存在下载记录，如果存在，则直接下载
            dr = DownloadRecord.objects.get(user=user, resource_url=resource_url, is_deleted=False)
            dr.update_time = datetime.datetime.now()
            dr.save()

            resource_ = check_oss(resource_url)

            if resource_:
                file = aliyun_oss_get_file(resource_.key)
                response = FileResponse(file)
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="' + parse.quote(resource_.filename,
                                                                                        safe=string.printable) + '"'
                return response
        except DownloadRecord.DoesNotExist:
            if user.valid_count <= 0:
                return HttpResponse('下载数已用完')

            # 更新用户的可用下载数和已用下载数
            user.valid_count -= 1
            user.used_count += 1
            user.save()

        # 生成资源存放的唯一子目录
        uuid_str = str(uuid.uuid1())
        sub_dir = os.path.join(settings.DOWNLOAD_DIR, uuid_str)
        os.mkdir(sub_dir)

        # 去除资源地址参数
        resource_url = resource_url.split('?')[0]

        if resource_url.startswith('https://download.csdn.net/download/'):
            logging.info('csdn resource download')

            # 这个今日资源下载数计算可能包含了以前下载过的资源，所以存在误差，偏大
            today_download_count = DownloadRecord.objects.filter(create_time__day=datetime.date.today().day,
                                                                 is_deleted=False).values('resource_url').distinct().count()
            if today_download_count == 20:
                recover(user)
                return JsonResponse(dict(code=403, msg='本站今日CSDN资源下载总数已达上限，请明日再来下载'))

            r = requests.get(resource_url)
            title = None
            if r.status_code == 200:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')

                    cannot_download = len(soup.select('div.resource_box a.copty-btn'))
                    if cannot_download:
                        return HttpResponse('版权受限，无法下载')
                    title = soup.select('dl.resource_box_dl span.resource_title')[0].string
                except Exception as e:
                    recover(user)
                    logging.error(e)
                    ding('资源名称获取失败 ' + str(e))
                    return HttpResponse('下载失败，平台进入维护状态')
            # 保存下载记录
            dr = DownloadRecord.objects.create(user=user, resource_url=resource_url, title=title)

            driver = get_driver()
            try:
                # 先请求，再添加cookies
                # selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
                driver.get('https://download.csdn.net')
                add_cookie(driver, settings.CSDN_COOKIES_FILE)

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

                filepath, filename = check_download(sub_dir)
                # 保存资源
                t = Thread(target=save_csdn_resource, args=(resource_url, filename, filepath, title))
                t.start()

                f = open(filepath, 'rb')
                response = FileResponse(f)
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename, safe=string.printable) + '"'
                return response

            except Exception as e:
                # 恢复用户可用下载数和已用下载数
                recover(user, dr)
                logging.error(e)
                ding(f'下载出现未知错误（{resource_url}） ' + str(e))
                return HttpResponse('下载失败，平台进入维护状态')

            finally:
                driver.quit()

        elif resource_url.startswith('https://wenku.baidu.com/view/'):
            logging.info('百度文库资源下载')

            driver = get_driver()
            try:
                driver.get('https://www.baidu.com/')
                add_cookie(driver, settings.WENKU_COOKIES_FILE)

                driver.get(resource_url)

                # VIP免费文档 共享文档 VIP专享文档 付费文档 VIP尊享8折文档
                doc_tag = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'bd doc-reader')]/div/div[contains(@style, 'display: block;')]/span"))
                ).text
                if doc_tag not in ['VIP免费文档', '共享文档', 'VIP专享文档']:
                    return HttpResponse('此类资源无法下载: ' + doc_tag)

                # 文档标题
                title = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'reader_ab_test with-top-banner')]/span"))
                ).text
                logging.info(title)

                # 文档标签，可能不存在
                # find_elements_by_xpath 返回的是一个List
                tags = [doc_tag]
                tag_els = driver.find_elements_by_xpath("//div[@class='tag-tips']/a")
                for tag_el in tag_els:
                    tags.append(tag_el.text)
                tags = settings.TAG_SEP.join(tags)
                logging.info(tags)

                # 文档分类
                cat_els = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@id='page-curmbs']/ul//a"))
                )[1:]
                cats = []
                for cat_el in cat_els:
                    cats.append(cat_el.text)
                cats = '-'.join(cats)
                logging.info(cats)

                # 保存下载记录
                dr = DownloadRecord.objects.create(user=user, resource_url=resource_url, title=title)

                # 显示下载对话框的按钮
                show_download_modal_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.reader-download.btn-download'))
                )
                show_download_modal_button.click()

                # 下载按钮
                try:
                    # 首次下载
                    download_button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.dialog-inner.tac > a.ui-bz-btn-senior.btn-diaolog-downdoc'))
                    )
                    # 取消转存网盘
                    cancel_wp_upload_check = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.wpUpload input'))
                    )
                    cancel_wp_upload_check.click()
                    download_button.click()
                except TimeoutException:
                    if doc_tag != 'VIP专享文档':
                        # 已转存过此文档
                        download_button = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'WkDialogOk'))
                        )
                        download_button.click()

                filepath, filename = check_download(sub_dir)
                # 保存资源
                t = Thread(target=save_wenku_resource, args=(resource_url, filename, filepath, title, tags, cats))
                t.start()

                f = open(filepath, 'rb')
                response = FileResponse(f)
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename, safe=string.printable) + '"'
                return response

            except Exception as e:
                # 恢复用户可用下载数和已用下载数
                recover(user, dr)
                logging.error(e)
                ding(f'下载出现未知错误（{resource_url}） ' + str(e))
                return HttpResponse('下载失败，平台进入维护状态')

            finally:
                driver.quit()

        else:
            return HttpResponse('错误的请求')

    else:
        return HttpResponse('错误的请求')


def save_csdn_resource(resource_url: str, filename: str, file: str, title: str) -> None:
    """
    保存CSDN资源记录并上传到oss

    :param resource_url:
    :param filename:
    :param file:
    :param title:
    :return:
    """
    # 判断资源记录是否已存在，如果已存在则直接返回
    if Resource.objects.filter(url=resource_url).count():
        return

    # 存储在oss中的key
    key = str(uuid.uuid1()) + '-' + filename
    upload_success = aliyun_oss_upload(file, key)
    if not upload_success:
        ding('阿里云OSS上传资源失败')
        return

    r = requests.get(resource_url)
    if r.status_code == 200:
        try:
            # 资源文件大小
            size = os.path.getsize(file)
            soup = BeautifulSoup(r.text, 'lxml')
            desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
            category = '-'.join([cat.string for cat in soup.select('div.csdn_dl_bread a')[1:3]])
            tags = settings.TAG_SEP.join([tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')])

            Resource.objects.create(title=title, filename=filename, size=size, desc=desc,
                                    url=resource_url, category=category, key=key, tags=tags)
        except Exception as e:
            logging.error(e)
            ding('资源信息保存失败 ' + str(e))
    else:
        ding('资源信息保存失败 - 资源请求失败')


def save_wenku_resource(resource_url: str, filename: str, file: str, title: str, tags: str, category: str) -> None:
    """
    保存百度文库资源记录并上传到oss

    :param resource_url:
    :param filename:
    :param file:
    :param title:
    :param tags:
    :param category:
    :return:
    """

    # 判断资源记录是否已存在，如果已存在则直接返回
    if Resource.objects.filter(url=resource_url).count():
        return

    # 存储在oss中的key
    key = str(uuid.uuid1()) + '-' + filename
    upload_success = aliyun_oss_upload(file, key)
    if not upload_success:
        ding('阿里云OSS上传资源失败')
        return

    try:
        # 资源文件大小
        size = os.path.getsize(file)
        Resource.objects.create(title=title, filename=filename, size=size,
                                url=resource_url, category=category, key=key, tags=tags)
    except Exception as e:
        logging.error(e)
        ding('资源信息保存失败 ' + str(e))


def order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception as e:
            logging.error(e)
            return JsonResponse(dict(code=400, msg='错误的请求'))

        total_amount = data.get('total_amount', None)
        purchase_count = data.get('purchase_count', None)
        code = data.get('code', None)

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

        subject = '购买CSDNBot下载服务'

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

                if not user.return_invitor:
                    user.return_invitor = True
                    # 优惠券
                    expire_time = datetime.datetime.now() + datetime.timedelta(days=7)
                    comment = '邀请新用户'
                    code = str(uuid.uuid1()).replace('-', '')
                    # 获取邀请人
                    u = User.objects.get(invite_code=user.invited_code)
                    Coupon(user=u, total_amount=0.8, purchase_count=1, expire_time=expire_time, comment=comment,
                           code=code).save()

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
        return JsonResponse(dict(code=200, msg='获取下载记录成功',
                                 download_records=DownloadRecordSerializers(download_records, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def service(request):
    if request.method == 'GET':
        services = Service.objects.all()
        return JsonResponse(dict(code=200, msg='获取服务成功', services=ServiceSerializers(services, many=True).data))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def health_check(request):
    if request.method == 'GET':
        is_healthy = Csdnbot.objects.get(id=1).is_healthy
        return JsonResponse(dict(code=200, is_healthy=is_healthy))


def upload(request):
    if request.method == 'POST':
        pass


def coupon(request):
    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))
        coupons = Coupon.objects.filter(user=user).all()
        return JsonResponse(dict(code=200, coupons=CouponSerializers(coupons, many=True).data))


def resource(request):
    if request.method == 'GET':
        page = int(request.GET.get('page', 1))
        key = request.GET.get('key', '')
        if page < 1:
            page = 1

        start = 5 * (page - 1)
        end = start + 5
        resources = Resource.objects.order_by('-create_time').filter(
            Q(title__contains=key) | Q(desc__contains=key) | Q(tags__contains=key)).all()[start:end]
        return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))


def resource_count(request):
    if request.method == 'GET':
        key = request.GET.get('key', '')
        return JsonResponse(dict(code=200, count=Resource.objects.filter(
            Q(title__contains=key) | Q(desc__contains=key) | Q(tags__contains=key)).count()))


def resource_download(request):
    """
    下载存储在oss上的资源

    :param request:
    :return:
    """

    if request.method == 'GET':
        key = request.GET.get('key', None)
        token = request.GET.get('token', None)
        if token is None or key is None:
            return HttpResponse('错误的请求')

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS512'])
        except Exception as e:
            logging.info(e)
            return HttpResponse('未认证')

        email = payload.get('sub', None)
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return HttpResponse('未认证')

        try:
            resource_ = Resource.objects.get(key=key)
            if not aliyun_oss_check_file(resource_.key):
                resource_.delete()
                return JsonResponse(dict(code=400, msg='资源已被删除'))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=400, msg='资源不存在'))

        try:
            dr = DownloadRecord.objects.get(user=user, resource_url=resource_.url, is_deleted=False)
            dr.update_time = datetime.datetime.now()
            dr.save()
        except DownloadRecord.DoesNotExist:
            if user.valid_count <= 0:
                return HttpResponse('下载数已用完')

            # 更新用户的可用下载数和已用下载数
            user.valid_count -= 1
            user.used_count += 1
            user.save()
            DownloadRecord.objects.create(user=user, resource_url=resource_.url, title=resource_.title)

        file = aliyun_oss_get_file(resource_.key)
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="' + parse.quote(resource_.filename, safe=string.printable) + '"'
        return response


def refresh_cookies(request):
    if request.method == 'GET':

        token = request.GET.get('rc_token', None)
        if token == settings.RC_TOKEN:
            if csdn_auto_login():
                return JsonResponse(dict(code=200, msg='cookies更新成功'))

            return JsonResponse(dict(code=500, msg='cookies更新失败'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))
    else:
        return JsonResponse(dict(code=400, msg='错误的请求'))


def wx(request):
    """
    微信公众号服务器接口
    https://mp.weixin.qq.com/advanced/advanced?action=interface&t=advanced/interface&token=508240585&lang=zh_CN

    接入文档
    https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Access_Overview.html

    开源SDK
    https://github.com/jxtech/wechatpy

    URL: https://api.csdnbot.ncucoder.com/wx/
    Token: 6zOpjsMV15xWihocay4grCRPY82EQS7m
    EncodingAESKey: KHh1qYYOoaioXgzHZYla00WSvuCGPlJhUtUNu6NOTIi

    请求参数
    signature	微信加密签名，signature结合了开发者填写的token参数和请求中的timestamp参数、nonce参数。
    timestamp	时间戳
    nonce	随机数
    echostr	随机字符串

    请求示例
    /wx/?signature=c047ea9c3b369811f237ef4145a0092b03e53149&echostr=4106217736181366575&timestamp=1580479503&nonce=14640658

    Django 返回字符串使用 return HttpResponse('str')

    :param request:
    :return:
    """
    if request.method == 'GET':
        """
        接入微信公众平台开发
        https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Access_Overview.html
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
        else:
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

        最终返回 xml
        
        示例请求
        POST /wx/?signature=78b016334f993e6701897e0dec278ea731af7d72&timestamp=1580552507&nonce=1302514634&openid=oc5rb00oVXaRUTRvvbIpCvDNSoFA&encrypt_type=aes&msg_signature=73ef0f95249e268641de2dc87761f234ca9d6db0
        路径参数
        signature
        timestamp
        nonce
        openid
        encrypt_type
        msg_signature
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

        # 关注/取消关注事件
        if msg.type == 'event':
            subscribe_event = SubscribeEvent(message=msg)
            logging.info(subscribe_event.event)

        reply = TextReply(message=msg)
        reply.content = 'CSDNBot reply'
        # 转换成 XML
        ret_xml = reply.render()
        # 加密
        encrypted_xml = crypto.encrypt_message(ret_xml, nonce, timestamp)
        return HttpResponse(encrypted_xml, content_type="text/xml")


def test(request):
    ret_data = {
        'xml': {
            'ToUserName': 'a',
            'FromUserName': 'b',
            'CreateTime': int(datetime.datetime.now().timestamp()),
            'MsgType': 'text',
            'Content': 'test'
        }
    }
    ret_xml = xmltodict.unparse(ret_data)
    return HttpResponse(ret_xml, content_type="text/xml")
