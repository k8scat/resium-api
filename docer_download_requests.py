# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/8

使用requests下载稻壳模板

"""
from json import JSONDecodeError

import requests


if __name__ == '__main__':
    resource_url = 'https://www.docer.com/preview/20259997'
    resource_id = resource_url.split('/')[-1]
    url = f'https://www.docer.com/detail/dl?id={resource_id}'
    headers = {
        'cookie': 'UM_distinctid=170186e42c31d6-0f0b9a23bac2b1-1d316653-13c680-170186e42c4b00; WAD=124966106TWw2; CNZZDATA1253016024=1752323090-1582975046-%7C1583167681; CNZZDATA1277687889=275378783-1580953873-https%253A%252F%252Fwww.google.com%252F%7C1583613565; Hm_lvt_97cef85273faacd28d711477de35d2eb=1583164517,1583496693,1583515295,1583614197; _vip_session_=a%3A5%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%2249c218159358bd02476d838aa8eaa0cb%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A11%3A%22100.67.95.5%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A120%3A%22Mozilla%2F5.0+%28Macintosh%3B+Intel+Mac+OS+X+10_15_3%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F80.0.3987.132+Safari%2F537.3%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1583614232%3Bs%3A9%3A%22user_data%22%3Bs%3A0%3A%22%22%3B%7Dd709a5fa065f8c9d26e2772c73d23c7f; BAIDU_SSP_lcr=https://account.wps.cn/loginCallbackApp?cb=https%3A%2F%2Fwww.docer.com%2Flogin%3Fcb_url%3Dhttps%253A%252F%252Fwww.docer.com%252Fs%252Fwpp%252F10125%253Fm_superkey%253Dsidenav%2526m_origin_scene%253Dsidenav%2526_xeci%253Dc0d5a88343b263a9c41eb1138a160a0d&from=miniprogramcode&reload=true&qrcode=docer&logintype=v1%2Fminiprogramcode; wps_sid=V02SPIEct-VYZCphNE4zNiL2fMEVGl800c4e33360000730164; Hm_lpvt_97cef85273faacd28d711477de35d2eb=1583614267',
    }
    with requests.get(url, headers=headers) as r:
        try:
            resp = r.json()
            if resp['result'] == 'ok':
                download_url = resp['data']
                filename = download_url.split('/')[-1]
                print(filename)
                # with requests.get(download_url) as _:
                #     # print(_.content)
                #     print(_.headers)
                #     print(_.status_code)
            else:
                print(resp)
        except JSONDecodeError:
            print(r.content)


