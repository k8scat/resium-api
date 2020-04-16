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
from django.http import HttpResponse

from downloader.models import DocerAccount, CsdnAccount, BaiduAccount
from downloader.utils import ding, get_random_ua


@api_view(['POST'])
def check_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    token = request.data.get('token', None)
    if token == settings.ADMIN_TOKEN:
        csdn_accounts = CsdnAccount.objects.all()
        for csdn_account in csdn_accounts:
            headers = {
                'cookie': csdn_account.cookies
            }
            with requests.get('https://download.csdn.net/my/vip', headers=headers) as r:
                soup = BeautifulSoup(r.text, 'lxml')
                el = soup.select('div.vip_info p:nth-of-type(1) span')
                if el:
                    ding(f'[CSDN] 剩余下载个数：{el[0].text}',
                         used_account=csdn_account.email)
                elif len(soup.select('div.name span')) > 0:
                    ding('[CSDN] Cookies仍有效',
                         used_account=csdn_account.email)
                else:
                    ding('[CSDN] Cookies已失效',
                         used_account=csdn_account.email)

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
                             used_account=baidu_account.email)
                    else:
                        ding('[百度文库] Cookies已失效',
                             used_account=baidu_account.email,
                             error=r.text,
                             logger=logging.error)

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
                         used_account=docer_account.email)
                else:
                    ding('稻壳模板cookies已失效，请尽快更新',
                         used_account=docer_account.email)
        except DocerAccount.DoesNotExist:
            ding('没有可以使用的稻壳模板会员账号')

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
                 used_account=csdn_account.email)
    return HttpResponse('')


@api_view(['POST'])
def check_qiantu_cookies(request):
    pass
