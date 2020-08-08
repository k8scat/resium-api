# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/8/9

"""
import requests
from resium.settings.base import ADMIN_TOKEN


def url(page, per_page=64):
    return f'http://docer.wps.cn/v3.php/api/search/shop_search?keyword=&page={page}&per_page={per_page}'


if __name__ == '__main__':

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
    }
    # 获取稻壳模板的资源列表
    current_page = 1
    while True:
        with requests.get(url(current_page), headers=headers) as r:
            if r.status_code == requests.codes.ok:
                res = r.json()
                if res.get('result', '') == 'ok':
                    resources = res['data']['data']
                    resources_len = len(resources)
                    if resources_len > 0:
                        if resources_len == 64:
                            current_page += 1
                        else:
                            exit(1)

                        for resource in resources:
                            resource_id = resource.get('id', '')
                            if not resource_id:
                                exit(1)
                            # 检查资源是否存在
                            docer_url = f'https://www.docer.com/preview/{resource_id}'
                            payload = {
                                'token': ADMIN_TOKEN,
                                'url': docer_url
                            }
                            with requests.post('https://api.resium.cn/check_docer_existed/', data=payload) as check_res:
                                if r.status_code == requests.codes.ok:
                                    res = check_res.json()
                                    if res['code'] == requests.codes.ok:
                                        if res['existed']:
                                            continue
                                        else:
                                            download_headers = {
                                                'Authorization': 'Bearer ' + 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI2NjY2NjYifQ.hcP4NzJUIigurnA0c1iXmE0H-kYaIogIz-iusKzf1jc1sL6VGm3ejnATQIPVNaB-oAWJSX1_KMKK9_KxvWCGvA',

                                            }
                                            payload = {
                                                'point': 1,
                                                'url': docer_url,
                                                't': 'url'
                                            }
                                            requests.post('https://api.resium.cn/download/',
                                                          headers=download_headers,
                                                          data=payload)

                    else:
                        exit(1)
