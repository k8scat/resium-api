# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

"""
import json
from time import sleep

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view
from selenium.webdriver.support.wait import WebDriverWait

from downloader.models import User, CsdnAccount
from downloader.serializers import UserSerializers
from downloader.utils import get_driver, ding
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


@api_view(['POST'])
def set_user_can_download(request):
    token = request.data.get('token', None)
    uid = request.data.get('uid', None)
    if token != settings.BOT_TOKEN or not uid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)

        if user.can_download:
            return JsonResponse(dict(code=400, msg='该账号已开启外站资源下载功能'))

        user.can_download = True
        user.save()
        return JsonResponse(dict(code=200, msg='成功设置用户可下载外站资源'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='用户不存在'))


@api_view(['POST'])
def get_user(request):
    token = request.data.get('token', None)
    uid = request.data.get('uid', None)
    if token != settings.BOT_TOKEN or not uid:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        user = User.objects.get(uid=uid)

        return JsonResponse(dict(code=200, user=UserSerializers(user).data))
    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='用户不存在'))


@api_view(['POST'])
def set_csdn_sms_validate_code(request):
    """
    保存CSDN下载短信验证码到数据库

    :param request:
    :return:
    """

    token = request.data.get('token', None)
    email = request.data.get('email', None)
    code = request.data.get('code', None)
    if token != settings.BOT_TOKEN or not code or not email:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        account = CsdnAccount.objects.get(email=email, need_sms_validate=True)
        account.sms_code = code
        account.save()

        return JsonResponse(dict(code=200, msg='验证码保存成功'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=404, msg='账号不存在'))


@api_view(['POST'])
def start_csdn_sms_validate(request):
    """
    CSDN下载短信验证

    :param request:
    :return:
    """

    token = request.data.get('token', None)
    email = request.data.get('email', None)
    if token != settings.BOT_TOKEN or not email:
        return JsonResponse(dict(code=400, msg='错误的请求'))

    try:
        account = CsdnAccount.objects.get(email=email, need_sms_validate=True)
        ding('开始处理CSDN验证码',
             used_account=account.email)
        driver = get_driver()
        try:
            driver.get('https://csdn.net')
            cookies = json.loads(account.driver_cookies)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                driver.add_cookie(cookie)

            driver.get('https://download.csdn.net/download/zdyanshi9/7995337')

            # 下载
            download_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[@class='c_dl_btn download_btn vip_download']"))
            )
            download_button.click()

            # 执行下载
            do_download_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[@class='dl_btn do_download vip_dl_btn']"))
            )
            do_download_button.click()

            # 获取验证码
            get_validate_code_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@id='validate-code']"))
            )
            get_validate_code_button.click()

            count = 0
            while True:
                account = CsdnAccount.objects.get(email=email)
                if account.sms_code:
                    break
                else:
                    if count >= 200:
                        return JsonResponse(dict(code=400, msg='验证码等待超时'))
                    ding('等待验证码...',
                         used_account=account.email)
                    sleep(3)

            # 验证码输入框
            validate_code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@id='validate-input']"))
            )
            validate_code_input.send_keys(account.sms_code)

            validate_confirm_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@id='sms-confirm']"))
            )
            validate_confirm_button.click()

            account.need_sms_validate = False
            account.sms_code = None
            account.save()

            return JsonResponse(dict(code=200, msg='短信验证成功'))

        finally:
            driver.close()

    except CsdnAccount.DoesNotExist:
        return JsonResponse(dict(code=400, msg='该账号不需要验证'))


@api_view(['POST'])
def get_csdn_accounts(request):
    """
    获取csdn账号信息

    :param request:
    :return:
    """

    token = request.data.get('token', None)
    if token != settings.BOT_TOKEN:
        return JsonResponse(dict(code=400, msg='错误的请求'))
    accounts = CsdnAccount.objects.all()
    msg = ''
    for index, account in enumerate(accounts):
        msg += '邮箱: ' + account.email + ' \n' + \
              '是否启用: ' + ('是' if account.is_enabled else '否') + ' \n' + \
              '是否需要短信验证: ' + ('是' if account.need_sms_validate else '否') + ' \n' + \
              '今日下载数: ' + str(account.today_download_count)
        if index < len(accounts)-1:
            msg += '\n\n'

    return JsonResponse(dict(code=200, msg=msg))
