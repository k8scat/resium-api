# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/24

"""
from json import JSONDecodeError

import requests

from downloader.utils import get_random_ua

if __name__ == '__main__':
    headers = {
        'cookie': '',
        'user-agent': get_random_ua(),
        'referer': 'https://download.csdn.net/upload',
        'origin': 'https://download.csdn.net',
        'content-type': 'multipart/form-data'
    }

    payload = {
    }

    with requests.post('https://download.csdn.net/upload', headers=headers, data=payload) as r:
        if r.status_code == requests.codes.OK:
            try:
                resp = r.json()
            except JSONDecodeError:
                exit(1)

            if resp['code'] == 200:
                # 上传成功
                pass
            else:
                # 上传失败
                pass

