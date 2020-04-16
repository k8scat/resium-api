# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/1

可能是千图网的bug，获取到下载链接后，个人中心并没有下载记录

"""
import requests

from downloader.apis.resource import QiantuResource


def download(url):
    headers = {
        'cookie': 'message2=1; qt_visitor_id=%22c39fc770e5af9c3879b7230e028e4a99%22; qtjssdk_2018_cross_new_user=1; loginTime=15; message2=1; imgCodeKey=%220e1fa5171e620fbf91e235a1dfa4a2c4%22; FIRSTVISITED=1586947095.189; Hm_lvt_41d92aaaf21b7b22785ea85eb88e7cea=1586947095; Hm_lvt_644763986e48f2374d9118a9ae189e14=1586947097; risk_forbid_login_uid=%2218573869%22; last_login_type=1; qt_risk_visitor_id=%2226f7e69c197e061270068bb190277e1d%22; ISREQUEST=1; WEBPARAMS=is_pay=0; han_data_is_pay:18573869=%222%22; qt_createtime=1586947193; awake=0; qt_ur_type=2; qiantudata2018jssdkcross=%7B%22distinct_id%22%3A%221717d6af7ab292-0e3aef30e258b9-396f7506-1296000-1717d6af7ac423%22%2C%22props%22%3A%7B%22latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22latest_referrer%22%3A%22%22%2C%22latest_referrer_host%22%3A%22%22%2C%22latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%7D; qt_type=2; source_lookp=%2235911629-%22; preseat=%u8BE6%u60C5%u9875%u6587%u5B57%u94FE; crm_collect_18573869_20200415=1; sns=%7B%22token%22%3A%7B%22access_token%22%3A%22B8EF398F08AD6FDB82595A8427817B2B%22%2C%22expires_in%22%3A%227776000%22%2C%22refresh_token%22%3A%22B006F2340B55B7250EA94C259F2AD147%22%2C%22openid%22%3A%22589C676151ABEB07EB6570F2A40EE4CB%22%7D%2C%22type%22%3A%22qq%22%7D; censor=%2220200415%22; loginCodeKey=%22loginCode41e111e2776dc9819d4ef357f2e7f36e%22; 58pic_btn=x_x_2; is_pay1586880000=%221%22; showAd:c39fc770e5af9c3879b7230e028e4a99=%22w6SIEgLKiJOIC5HVD3fKoMmZowzJnZCWztvHzJLJmZG6owi6mJmWztaYogu3ytK8iIWIywr5zxj3AxnLCL2Pzci9iJeIlcj3DxjUiJOXlcjZAg26x6rPBwvZiJO7lcjSyxn3x6nOB6DFDgLTzsi9mtu7nJK4mdC5n63SEYj7AwqIoIjZAg26qwq9yZm8zMm6nZbLnwfMowmZodC8yJCYmZbLmdi7ztrHotKIlcjHzhzLCNrPC5vYx5LKiJOInsiSiNr4CM7IoJeSiNnOB6DFDgLTzxmIoIi3iIWIBgfZDf2ZAg26x6rPBwuIoJe4ody8nta7mdb2xq%3D%3D%22; loginBackUrl=%22https%3A%5C%2F%5C%2Fwww.58pic.com%5C%2Fnewpic%5C%2F35911629.html%22; popupShowNum=4; originUrl=https%3A%2F%2Fwww.58pic.com%2Flogin; auth_id=%2218573869%7CTkNV56iL5bqP5aqb%7C1587556841%7Ca3b9594a8dc2f5b4397d35f590ed4934%22; success_target_path=%22https%3A%5C%2F%5C%2Fwww.58pic.com%5C%2Fnewpic%5C%2F35911629.html%22; ssid=%225e96f7694f1de4.23004900%22; _is_pay=1; _auth_dl_=MTg1NzM4Njl8MTU4NzU1Njg0MXw4MWZhMjQxMmVlZDA1N2ZkMzcyODEwZGQyZmJkNzNlMA%3D%3D; qt_uid=%2218573869%22; last_view_picid=%2235825335%22; Hm_lpvt_644763986e48f2374d9118a9ae189e14=1586952245; Hm_lpvt_41d92aaaf21b7b22785ea85eb88e7cea=1586952273; qt_utime=1586952273',
        'referer': url,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
    }
    download_url = url.replace('https://www.58pic.com/newpic/', 'https://dl.58pic.com/')
    with requests.get(download_url, headers=headers) as r:
        print(r.text)
        print(r.status_code)


if __name__ == '__main__':
    url = 'https://www.58pic.com/newpic/35911964.html'
    # download(url)
    resource = QiantuResource(url)








