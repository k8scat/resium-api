# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/6/18

"""

import os
import re
import time

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()

import requests
from downloader.utils import send_email


def check_file():
    lines = []
    num = 1
    with open('links.txt', 'r') as f:
        while True:
            line = f.readline().strip()
            if not line:
                break

            line = re.split(r' +', line)
            if len(line) != 2:
                print(num)
                return None

            num += 1
            lines.append(line)

    return lines


def download(num, url, email):
    data = {
        'url': url,
        't': 'url',
        'point': 10
    }
    headers = {
        'Authorization': 'Bearer ' + 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI2NjY2NjYifQ.hcP4NzJUIigurnA0c1iXmE0H-kYaIogIz-iusKzf1jc1sL6VGm3ejnATQIPVNaB-oAWJSX1_KMKK9_KxvWCGvA'
    }
    with requests.post('https://api.resium.cn/download/', data, headers=headers) as r:
        if r.status_code == requests.codes.ok:
            res_data = r.json()
            if res_data['code'] == requests.codes.ok:
                send_email('资源下载成功', res_data['url'], email)
                print(f'Download success: {num}')
            else:
                print(f'Download fail: {num}, {res_data["msg"]}')
        else:
            print(f'Request fail: {num}')


if __name__ == '__main__':
    lines = check_file()
    if lines:
        for index, line in enumerate(lines):
            url, email = line
            url = url.split('?')[0]
            download(index+1, url, email)
            time.sleep(3600)
