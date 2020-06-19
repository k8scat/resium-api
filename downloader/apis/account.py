# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import json
import logging

import requests
from bs4 import BeautifulSoup
from rest_framework.decorators import api_view
from django.conf import settings
from django.http import HttpResponse, JsonResponse

from downloader.decorators import auth
from downloader.models import DocerAccount, CsdnAccount, BaiduAccount, QiantuAccount, User
from downloader.serializers import CsdnAccountSerializers
from downloader.utils import ding, get_random_ua, get_csdn_valid_count, send_email, get_csdn_id, qq_send_group_msg


@api_view(['POST'])
def check_csdn_cookies(request):
    """
    检查CSDN cookies
    """

    token = request.data.get('token', None)
    if token == settings.ADMIN_TOKEN:
        csdn_accounts = CsdnAccount.objects.all()
        for csdn_account in csdn_accounts:
            valid_count = get_csdn_valid_count(csdn_account.cookies)
            if valid_count is None:
                csdn_account.is_disabled = True
                csdn_account.is_cookies_valid = False
                csdn_account.save()
                msg = f'CSDN会员账号（ID为{csdn_account.csdn_id}）的Cookies已失效，为了保障会员账号的可用性，请及时登录网站（https://resium.cn/user）进行重新设置Cookies，如有疑问请联系管理员！【此消息来自定时任务，如已知悉请忽略】'
                send_email(
                    subject='[源自下载] CSDN账号提醒',
                    content=msg,
                    to_addr=csdn_account.user.email
                )
                qq_send_group_msg(group_id=settings.PATTERN_GROUP_ID,
                                  msg=msg,
                                  at_member=csdn_account.qq)
                ding('[CSDN] Cookies已失效',
                     download_account_id=csdn_account.id)
            else:
                if valid_count == 0:
                    csdn_account.is_disabled = True
                    msg = f'CSDN会员账号（ID为{csdn_account.csdn_id}）的会员下载数已用尽，请知悉！【此消息来自定时任务，如已知悉请忽略】'
                    send_email(
                        subject='[源自下载] CSDN账号提醒',
                        content=msg,
                        to_addr=csdn_account.user.email
                    )
                    qq_send_group_msg(group_id=settings.PATTERN_GROUP_ID,
                                      msg=msg,
                                      at_member=csdn_account.qq)
                else:
                    if csdn_account.need_sms_validate:
                        msg = f'CSDN会员账号（ID为{csdn_account.csdn_id}）需要进行短信验证，为了保障会员账号的可用性，请及时进行短信验证并登录网站（https://resium.cn/user）解除短信验证，如有疑问请联系管理员！【此消息来自定时任务，如已知悉请忽略】'
                        send_email(
                            subject='[源自下载] CSDN账号提醒',
                            content=msg,
                            to_addr=csdn_account.user.email
                        )
                        qq_send_group_msg(group_id=settings.PATTERN_GROUP_ID,
                                          msg=msg,
                                          at_member=csdn_account.qq)
                ding(f'[CSDN] 剩余下载个数：{valid_count}',
                     download_account_id=csdn_account.id)
                csdn_account.valid_count = valid_count
                csdn_account.save()

    return HttpResponse('')


@api_view(['POST'])
def check_baidu_cookies(request):
    """
    检查百度 cookies
    """
    token = request.data.get('token', None)
    if token == settings.ADMIN_TOKEN:
        baidu_accounts = BaiduAccount.objects.all()
        for baidu_account in baidu_accounts:
            cookies = ''
            for cookie in json.loads(baidu_account.cookies):
                cookies += f"{cookie['name']}={cookie['value']};"
            headers = {
                'referer': 'https://wenku.baidu.com',
                'cookie': cookies,
                'user-agent': get_random_ua()
            }
            get_user_info_url = 'https://wenku.baidu.com/user/interface/getuserinfo'
            with requests.post(get_user_info_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    data = r.json()['data']
                    is_login = data['userInfo']['isLogin']
                    if is_login:
                        share_doc_count = data['jiaoyu_vip_info']['download_ticket_count']
                        vip_special_doc_count = data['jiaoyu_vip_info']['professional_download_ticket_count']
                        ding(f'[百度文库] 可用共享文档下载特权 {share_doc_count} 次，可用VIP专享文档下载特权 {vip_special_doc_count} 次',
                             download_account_id=baidu_account.id)
                    else:
                        ding('[百度文库] Cookies已失效',
                             download_account_id=baidu_account.id,
                             error=r.text,
                             logger=logging.error,
                             need_email=True)

    return HttpResponse('')


@api_view(['POST'])
def check_docer_cookies(request):
    """
    检查稻壳模板 cookies
    """
    token = request.data.get('token', None)
    if token == settings.ADMIN_TOKEN:
        try:
            docer_account = DocerAccount.objects.get(is_enabled=True)
            headers = {
                'cookie': docer_account.cookies
            }
            url = 'https://www.docer.com/proxy-docer/v4.php/api/user/allinfo'
            with requests.get(url, headers=headers) as r:
                if r.json()['result'] == 'ok':
                    ding('稻壳模板cookies仍有效',
                         download_account_id=docer_account.id)
                else:
                    ding('稻壳模板cookies已失效，请尽快更新',
                         download_account_id=docer_account.id,
                         need_email=True)
        except DocerAccount.DoesNotExist:
            ding('没有可以使用的稻壳模板会员账号',
                 need_email=True)

    return HttpResponse('')


@api_view(['POST'])
def reset_csdn_today_download_count(request):
    """
    重置CSDN账号的今日已下载数
    """
    token = request.data.get('token', None)
    if token == settings.ADMIN_TOKEN:
        csdn_accounts = CsdnAccount.objects.all()
        for csdn_account in csdn_accounts:
            csdn_account.today_download_count = 0
            csdn_account.save()
            ding('[CSDN] 今日下载数已重置',
                 download_account_id=csdn_account.id)
            logging.info(f'CSDN账号 {csdn_account.id} 已重置今日下载数')
    return HttpResponse('')


@api_view(['POST'])
def check_qiantu_cookies(request):
    qiantu_accounts = QiantuAccount.objects.all()
    for qiantu_account in qiantu_accounts:
        headers = {
            'cookie': qiantu_account.cookies,
            'referer': 'https://www.58pic.com/newpic/35979263.html',
            'user-agent': get_random_ua()
        }
        with requests.get('https://dl.58pic.com/35979263.html', headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.text, 'lxml')
                # download_url = soup.select('a.clickRecord.autodown')[0]['href']
                if len(soup.select('a.clickRecord.autodown')) > 0:
                    ding('[千图网] Cookies仍有效',
                         download_account_id=qiantu_account.id)
                else:
                    ding('[千图网] Cookies已失效, 请尽快更新！',
                         download_account_id=qiantu_account.id,
                         need_email=True)
    return HttpResponse('')


@auth
@api_view(['POST'])
def add_or_update_csdn_account(request):
    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)
    if not user.is_pattern:
        return JsonResponse(dict(code=requests.codes.forbidden, msg='无权访问'))

    cookies = request.data.get('cookies', None)
    csdn_account_id = request.data.get('id', None)

    valid_count = get_csdn_valid_count(cookies)
    csdn_id = get_csdn_id(cookies)
    if valid_count is None or not csdn_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='无效的cookies'))
    if valid_count == 0:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='CSDN会员账号剩余可用下载数为零！'))

    if csdn_account_id:
        try:
            csdn_account = CsdnAccount.objects.get(id=csdn_account_id, csdn_id=csdn_id, user=user)
            csdn_account.cookies = cookies
            csdn_account.valid_count = valid_count
            csdn_account.is_cookies_valid = True
            csdn_account.is_disabled = False
            csdn_account.save()
            return JsonResponse(dict(code=requests.codes.ok, msg='成功更新CSDN会员账号的Cookies'))

        except CsdnAccount.DoesNotExist:
            return JsonResponse(dict(code=requests.codes.not_found, msg='CSDN账号不存在'))
    else:
        if CsdnAccount.objects.filter(csdn_id=csdn_id).count() > 0:
            return JsonResponse(dict(code=requests.codes.bad_request, msg='CSDN账号已存在，请勿重复添加！'))

        CsdnAccount(user=user, cookies=cookies, valid_count=valid_count, csdn_id=csdn_id).save()
        return JsonResponse(dict(code=requests.codes.ok, msg='成功添加CSDN会员账号'))


@auth
@api_view()
def list_csdn_accounts(request):
    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)
    csdn_accounts = CsdnAccount.objects.filter(user=user).all()
    return JsonResponse(dict(code=requests.codes.ok, csdn_accounts=CsdnAccountSerializers(csdn_accounts, many=True).data))


@auth
@api_view()
def remove_csdn_sms_validate(request):
    csdn_account_id = request.GET.get('id', None)
    if not csdn_account_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)
    try:
        csdn_account = CsdnAccount.objects.get(id=csdn_account_id, user=user)
        csdn_account.need_sms_validate = False
        csdn_account.save()
        return JsonResponse(dict(code=requests.codes.ok, msg='成功解除CSDN会员账号的短信验证'))
    except CsdnAccount.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.forbidden, msg='禁止操作'))
