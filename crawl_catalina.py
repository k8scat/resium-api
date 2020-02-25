# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/20

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()

import re
import uuid
import requests
from csdnbot.settings import base
from bs4 import BeautifulSoup
from downloader.utils import aliyun_oss_upload, get_file_md5
from downloader.models import Resource, User


def download(resource_id):
    # 这个cookies直接从浏览器的network里复制过来就可以
    cookies = '__RequestVerificationToken=xluoXkyiqJxowhZ5eX9cSUs3PTz0oAZ6Mpz_Tn75LZopRLpWJEP8PljFN6SVHICU-EUYYBrfE6-ay4zRQbXbeKA3qWE1; Hm_lvt_9bce086c3196aa2e6e9eaa6e52fac052=1581903454,1581927770,1582183298; ASP.NET_SessionId=gtd152b4b1av1mfnnid5rbxf; wrawrsatrsrweasrdxsfw2ewasjret=; wrawrsatrsrweasrdxsf=; __Authentication=2F052D5461BF50F9D2A4BEC14FE41856D977F4DE5B81150D0C9817A6CF1A34D42815169F51F937780B43D8051BE65B4F636D142DD3601D3D6951016171167646B238240206C272E84EDBC44FCF39228FEDF5AA0523D2F3CABA04BA61CFBFD1BE2E447E91; like=s3c2440.zip; Hm_lpvt_9bce086c3196aa2e6e9eaa6e52fac052=1582189145'
    cookies = cookies.replace(' ', '').split(';')
    cookies_dict = {}
    for cookie in cookies:
        cookie = cookie.split('=')
        cookies_dict.setdefault(cookie[0], cookie[1])
    download_base_url = 'http://www.catalina.com.cn/access/downfile?id='
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.106 Safari/537.36',
        'referer': f'http://www.catalina.com.cn/info_{resource_id}.html',
        'host': 'www.catalina.com.cn',
        'connection': 'keep-alive',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8'
    }
    r = requests.get(download_base_url + resource_id, headers=headers, cookies=cookies_dict)
    if r.status_code == 200:
        oss_url = r.content.decode()
        if re.match(r'^http://sheldonbucket\.oss-cn-shanghai\.aliyuncs\.com/.+', oss_url):
            r = requests.get(oss_url)

            save_dir = os.path.join(base.DOWNLOAD_DIR, str(uuid.uuid1()))
            os.mkdir(save_dir)
            # 文件名
            filename = r.headers['Content-Disposition'].split('=')[1]
            # 文件大小
            size = int(r.headers['Content-Length'])
            # 文件存储路径
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(r.content)

            return filename, size, filepath, save_dir


def parse():
    t = 2
    p = 1
    while True:
        if p == 1:
            url = f'http://www.catalina.com.cn/Access/c-{t}'
        else:
            url = f'http://www.catalina.com.cn/Access/cp-{t}-{p}'
        r = requests.get(url)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'lxml')
            items = soup.find('ul', class_='list-unstyled jh-library-item').find_all('li', recursive=False)
            for item in items:
                content = item.find_all('a')
                if content[0].string == '【免费】':
                    save_dir = None
                    try:
                        resource_id = re.findall(r'\d+', content[1]['href'])[0]
                        title = content[1].string
                        desc = content[2].string
                        filename, size, filepath, save_dir = download(resource_id)
                        with open(filepath, 'rb') as f:
                            file_md5 = get_file_md5(f)
                            if Resource.objects.filter(file_md5=file_md5).count():
                                continue
                        r = requests.get(f'http://www.catalina.com.cn/info_{resource_id}.html')
                        if r.status_code == 200:
                            soup = BeautifulSoup(r.text, 'lxml')
                            tags = soup.find('div', class_='divTags').find_all('span')
                            tags = base.TAG_SEP.join([tag.string.strip() for tag in tags])
                        else:
                            tags = ''
                        key = f'{str(uuid.uuid1())}-{filename}'
                        if aliyun_oss_upload(filepath, key):
                            Resource(title=title, desc=desc, filename=filename,
                                     size=size, file_md5=file_md5, category='移动开发-Android',
                                     tags=tags, key=key, download_count=0, user=user).save()
                    finally:
                        if save_dir:
                            os.system(f'rm -rf {save_dir}')

            p += 1
        else:
            break


if __name__ == '__main__':
    user = User.objects.get(email='hsowan.me@gmail.com', is_active=True)
    parse()

