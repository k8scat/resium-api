# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/8

使用requests下载csdn资源

"""
import requests
from bs4 import BeautifulSoup


def csdn_download(url):
    with requests.get(url) as r:
        soup = BeautifulSoup(r.text, 'lxml')
        # 版权受限，无法下载
        # https://download.csdn.net/download/c_baby123/10791185
        cannot_download = len(soup.select('div.resource_box a.copty-btn'))
        if cannot_download:
            return False
        # 获取资源标题
        title = soup.select('div.resource_box_info span.resource_title')[0].string
        desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
        category = '-'.join([cat.string for cat in soup.select('div.csdn_dl_bread a')[1:3]])
        tags = [tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')]

    resource_id = url.split('/')[-1]
    headers = {
        'cookie': 'download_first=1; WM_TID=ThLNgEIe%2BL9BQVUEUBds1N3VFR2rte2Z; __yadk_uid=ZvWJtgSQwICVv2HlbKLYCmFSaYihKfXw; WM_NI=1I6mTZyL%2FVpWCrIMFFnzD8NkwYBi8f4lTH88%2F2HanZ3VIXmT4Lr1vNR0pjkM4%2B4VnXdiTuk5d5LXI5wXyS7jz45%2Bhf99FstfaIaBgHVWq5n9A4uTkLuI%2BEr969UJiUIOeTY%3D; WM_NIKE=9ca17ae2e6ffcda170e2e6ee89d1219ab897a8f27b91b08fa3d45e929f9a84f26788b8c096c93aac989f82fb2af0fea7c3b92af397fa8ed752bb94e1b7f35d81ae87aec54eaea68cd9cd61b5878e8abb6ef8b49ca9bb34edee8882ed52f18a87b9f060f894bed2f54692f0c08bea47f8f5fcb7ed54a8b79c96ea3fa8eb84b9cc3fb588b7b4b662baecfbcceb6efbe78a94f76ea397afa3e6449689bfd6ed3383ecbbb5ea48b797e5a6f133f6e79babec5f8b91abb5dc37e2a3; uuid_tt_dd=10_19729187150-1566015544503-471487; dc_session_id=10_1566015544503.833950; smidV2=201812152332371d7504c82c0bff6a7529b396d2f3edb500b8a473d5608ab90; Hm_ct_e5ef47b9f471504959267fd614d579cd=5744*1*ken1583096683!6525*1*10_19729187150-1566015544503-471487; CloudGuest=XYXyUF+oCeSMVxvIIRt3JWRiucjgst0wq2bh7Y2MMmKwfzndxnW75PeYjSQpBvjlAjSyo04O+Mx177VGKuGiUzmzGe/9LjYCDSrtw7w2Ey0AO2GKZGH4C5OdVJ5LO2CZ+Y8SGjXO5xFmqUxAHM4dph6mWDP6z3TAqVcLhyxzz61TNazM7jhwY96z5Lwzn5oq; __gads=ID=aa8b3baefd95d94b:T=1580283073:S=ALNI_MashEi2REUrd_hgkQNaUrqD_pW_Vw; _ga=GA1.2.2064109157.1580912221; Hm_lvt_e5ef47b9f471504959267fd614d579cd=1579800939,1580592841,1581723731; UM_distinctid=170974d7fda8e3-05b20d0883a9a8-396c7406-13c680-170974d7fdbaa9; UN=ken1583096683; Hm_ct_6bcd52f51e9b3dce32bec4a3997715ac=5744*1*ken1583096683!1788*1*PC_VC!6525*1*10_19729187150-1566015544503-471487; _gid=GA1.2.2026855164.1583490421; UserName=ken1583096683; UserInfo=478c762fb097493492a3d04e6eefdfa9; UserToken=478c762fb097493492a3d04e6eefdfa9; UserNick=hsowan; AU=68B; BT=1583507723455; p_uid=U100000; firstDie=1; announcement=%257B%2522isLogin%2522%253Atrue%252C%2522announcementUrl%2522%253A%2522https%253A%252F%252Fblog.csdn.net%252Fblogdevteam%252Farticle%252Fdetails%252F103603408%2522%252C%2522announcementCount%2522%253A0%252C%2522announcementExpire%2522%253A3600000%257D; Hm_lvt_6bcd52f51e9b3dce32bec4a3997715ac=1583476661,1583490420,1583573668,1583612965; TY_SESSION_ID=3a93f84e-a712-4d15-b82a-c8b5e2d0925d; dc_tos=q6ublq; c_ref=https%3A//download.csdn.net/my/downloads; Hm_lpvt_6bcd52f51e9b3dce32bec4a3997715ac=1583612991; aliyun_webUmidToken=TDEF2C18B979EFA3853AA6ABE98E19E6050DF77C46E8953F14B1319B993',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
        'referer': url  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
    }
    with requests.get(f'https://download.csdn.net/source/download?source_id={resource_id}', headers=headers) as r:
        resp = r.json()
        print(resp)
        if resp['code'] == 200:
            with requests.get(resp['data'], headers=headers) as _:
                print(_.content)
                print(_.status_code)
                print(_.headers)


if __name__ == '__main__':
    url = 'https://download.csdn.net/download/qq_24734285/12152656'


