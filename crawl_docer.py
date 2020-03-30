# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/29

爬取docer资源

"""
import json
import os
import time

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

import requests
from django.conf import settings

from downloader.utils import ding


def get_resources(keyword='', page=1):
    url = 'https://docer.wps.cn/v3.php/api/search/shop_search?per_page=64&sale_type=2'
    params = {
        'keyword': keyword,
        'page': page,
        'per_page': 99,
        'sale_type': 1,
        'mb_app': '1,2,3'
    }
    with requests.get(url, params=params) as r:
        if r.status_code == requests.codes.OK and r.json()['result'] == 'ok':
            return [resource['id'] for resource in r.json()['data']['data']]


def download(resource_id):
    url1 = f'https://www.docer.com/preview/{resource_id}'
    url2 = f'https://www.docer.com/webmall/preview/{resource_id}'
    headers = {
        'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJoc293YW4ubWVAZ21haWwuY29tIn0.GccYzRBABvxQ6ryFUdFEEzz77SBjC3GxleM9uSP-uJuLKpGgYriSANRJDWWNk8VbSyVGtgaTj0yS-pSyvad_KQ'
    }
    payload1 = {
        'url': url1
    }
    payload2 = {
        'url': url2
    }
    with requests.post('https://api.resium.cn/check_resource_existed/', data=payload1, headers=headers) as r1:
        if r1.status_code == requests.codes.OK and r1.json()['code'] == 200 and not r1.json()['is_existed']:
            with requests.post('https://api.resium.cn/check_resource_existed/', data=payload2, headers=headers) as r2:
                if r2.status_code == requests.codes.OK and r2.json()['code'] == 200 and not r2.json()['is_existed']:
                    with requests.post('https://api.resium.cn/download/', data=payload1, headers=headers) as download_resp:
                        if download_resp.headers.get('Content-Type', None) == 'application/octet-stream':
                            ding('稻壳模板下载成功', resource_url=url1)
                            return True
    return False


if __name__ == '__main__':
    # 获取稻壳模板的ID并保存到文件
    # total_resources = []
    # current_page = 1
    # resources = get_resources(page=current_page)
    # while len(resources):
    #     for res in resources:
    #         if res not in total_resources:
    #             total_resources.append(res)
    #     current_page += 1
    #     resources = get_resources(page=current_page)
    # with open(os.path.join(settings.BASE_DIR, 'docer_resources.json'), 'w') as f:
    #     f.write(json.dumps({
    #         'resources': total_resources
    #     }))

    with open(os.path.join(settings.BASE_DIR, 'docer_resources.json'), 'r') as f:
        resources = json.loads(f.read())['resources']
        count = 0
        for res_id in resources[:260]:

            if download(res_id):
                count += 1
            time.sleep(300)

        ding(f'最终爬取了{count}个稻壳模板')
