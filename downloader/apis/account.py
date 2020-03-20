# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/25

"""
import requests
from bs4 import BeautifulSoup
from rest_framework.decorators import api_view
from django.conf import settings
from django.http import HttpResponse

from downloader.models import DocerAccount, CsdnAccount, BaiduAccount
from downloader.utils import ding


@api_view(['POST'])
def check_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    if request.method == 'POST':
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
                        ding(f'CSDN会员账号剩余下载个数: {el[0].text}')
                    else:
                        ding('CSDN会员账号的cookies已失效，请及时更新')

        return HttpResponse('')


@api_view(['POST'])
def check_baidu_cookies(request):
    """
    检查百度 cookies
    """
    if request.method == 'POST':
        token = request.data.get('token', None)
        if token == settings.ADMIN_TOKEN:
            baidu_accounts = BaiduAccount.objects.all()
            for baidu_account in baidu_accounts:
                headers = {
                    'referer': 'https://wenku.baidu.com',
                    'cookie': baidu_account.cookies,
                    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
                }
                get_user_info_url = 'https://wenku.baidu.com/user/interface/getuserinfo'
                with requests.post(get_user_info_url, headers=headers) as r:
                    if r.status_code == requests.codes.OK:
                        is_login = r.json()['data']['userInfo']['isLogin']
                        if is_login:
                            ding('百度文库cookies仍有效')
                        else:
                            ding(f'百度文库cookies已失效，{r.text}')

        return HttpResponse('')


@api_view(['POST'])
def check_docer_cookies(request):
    """
    检查稻壳模板 cookies
    """
    if request.method == 'POST':
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
                        ding('稻壳模板cookies仍有效')
                    else:
                        ding('稻壳模板cookies已失效，请尽快更新')
            except DocerAccount.DoesNotExist:
                ding('没有可以使用的稻壳模板会员账号')

        return HttpResponse('')


@api_view(['POST'])
def reset_csdn_today_download_count(request):
    """
    重置CSDN账号的今日已下载数
    """

    if request.method == 'POST':
        token = request.data.get('token', None)
        if token == settings.ADMIN_TOKEN:
            csdn_accounts = CsdnAccount.objects.all()
            for csdn_account in csdn_accounts:
                csdn_account.today_download_count = 0
                csdn_account.save()
        return HttpResponse('')
