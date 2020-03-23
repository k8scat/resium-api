# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/12

爬取CSDN账号已下载资源

"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

import uuid
from threading import Thread
from urllib import parse
import requests
from bs4 import BeautifulSoup
from downloader.utils import save_resource
from downloader.models import CsdnAccount, User, Resource
from django.conf import settings


def check_download(resource_url):
    print(f'开始检查资源: {resource_url}')
    session.headers.setdefault('referer', resource_url)
    resource_id = resource_url.split('/')[-1]
    before_download_url = f'https://download.csdn.net/source/before_download?source_id={resource_id}'
    with session.get(before_download_url, headers=headers) as r:
        if r.status_code == requests.codes.OK and r.json()['code'] == 200:
            has_download = r.json()['data']['has_download']
            if has_download:
                if not Resource.objects.filter(url=resource_url).count():
                    print('开始下载')
                    with session.get(f'https://download.csdn.net/source/download?source_id={resource_id}', headers=headers) as r_:
                        resp = r_.json()
                        if resp['code'] == 200:
                            with session.get(resource_url) as _:
                                soup = BeautifulSoup(_.text, 'lxml')
                                # 版权受限，无法下载
                                # https://download.csdn.net/download/c_baby123/10791185
                                cannot_download = len(soup.select('div.resource_box a.copty-btn'))
                                if cannot_download:
                                    print('版权受限，无法下载')
                                    return
                                # 获取资源标题
                                title = soup.select('div.resource_box_info span.resource_title')[0].string
                                desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
                                category = '-'.join([cat.string for cat in soup.select('div.csdn_dl_bread a')[1:3]])
                                tags = settings.TAG_SEP.join([tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')])

                            with requests.get(resp['data'], headers=headers, stream=True) as _:
                                if _.status_code == requests.codes.OK:
                                    filename = parse.unquote(_.headers['Content-Disposition'].split('"')[1])

                                    # 生成资源存放的唯一子目录
                                    unique_folder = str(uuid.uuid1())
                                    save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
                                    while True:
                                        if os.path.exists(save_dir):
                                            unique_folder = str(uuid.uuid1())
                                            save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
                                        else:
                                            os.mkdir(save_dir)
                                            break
                                    filepath = os.path.join(save_dir, filename)
                                    # 写入文件，用于线程上传资源到OSS
                                    with open(filepath, 'wb') as f:
                                        for chunk in _.iter_content(chunk_size=1024):
                                            if chunk:
                                                f.write(chunk)
                                    # 上传资源到OSS并保存记录到数据库
                                    t = Thread(target=save_resource, args=(resource_url, filename, filepath, title, tags, category, desc, user))
                                    t.start()
                                else:
                                    print(_.content)
                                    exit(1)
                else:
                    print('资源已存在，跳过')
            else:
                print(r.json())
                exit(1)


def parse_resources(page):
    print(f'开始爬取第{page}页')
    with session.get(f'https://download.csdn.net/my/downloads/{page}', headers=headers) as r:
        if r.status_code == requests.codes.OK:
            soup = BeautifulSoup(r.text, 'lxml')
            resources = soup.select('div.card div.content h3 a')
            for resource in resources:
                check_download(f"https://download.csdn.net{resource['href']}")

            if resources:
                parse_resources(page+1)


if __name__ == '__main__':
    csdn_account = CsdnAccount.objects.get(email='17770040362@163.com')
    user = User.objects.get(email='hsowan.me@gmail.com', is_active=True)
    headers = {
        'cookie': csdn_account.cookies,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'
    }
    session = requests.session()
    session.headers = headers

    parse_resources(1)
