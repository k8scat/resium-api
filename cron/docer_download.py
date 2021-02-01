# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/8/9

"""
import json

import requests


def url(page, per_page=64):
    return f'http://docer.wps.cn/v3.php/api/search/shop_search?keyword=&page={page}&per_page={per_page}'


if __name__ == '__main__':

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
    }
    # 获取稻壳模板的资源列表
    current_page = 1
    while True:
        print(f'当前页：{current_page}')
        current_url = url(current_page)
        with requests.get(current_url, headers=headers) as r:
            if r.status_code == requests.codes.ok:
                print(f'Get {current_url} {r.status_code}')
                res = r.json()
                if res.get('result', '') == 'ok':
                    resources = res['data']['data']
                    resources_len = len(resources)
                    print(f'稻壳模板列表获取成功：{resources_len}')
                    if resources_len > 0:
                        if resources_len == 64:
                            current_page += 1
                        else:
                            print(f'没有更多稻壳模板了，当前页：{current_url}')
                            exit(1)

                        for resource in resources:
                            resource_id = resource.get('id', '')
                            if not resource_id:
                                print(f'稻壳模板ID获取失败：{json.dumps(resource)}')
                                exit(1)
                            # 检查资源是否存在
                            docer_url = f'https://www.docer.com/preview/{resource_id}'
                            payload = {
                                'token': 'csSM0Aw4NrvpZfxDEtbB3mPCWVUK52OnQik9djuLz1Ih8aToGJ',
                                'url': docer_url
                            }
                            with requests.post('https://api.resium.ncucoder.com/check_docer_existed/', data=payload) as check_res:
                                if r.status_code == requests.codes.ok:
                                    res = check_res.json()
                                    if res['code'] == requests.codes.ok:
                                        if res['existed']:
                                            print(f'资源已存在，跳过：{docer_url}')
                                            continue
                                        else:
                                            download_headers = {
                                                'Authorization': 'Bearer ' + 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI2NjY2NjYifQ.hcP4NzJUIigurnA0c1iXmE0H-kYaIogIz-iusKzf1jc1sL6VGm3ejnATQIPVNaB-oAWJSX1_KMKK9_KxvWCGvA'
                                            }
                                            payload = {
                                                'point': 1,
                                                'url': docer_url,
                                                't': 'url'
                                            }
                                            requests.post('https://api.resium.ncucoder.com/download/',
                                                          headers=download_headers,
                                                          data=payload)
                                            print(f'下载请求发送成功：{docer_url}')
                                            exit(0)
                                else:
                                    print(f'接口请求失败：{check_res.status_code}')

                    else:
                        print(f'当前页没有更多稻壳模板了：{current_url}')
                        exit(1)
                else:
                    print(f'稻壳模板列表获取失败：{json.dumps(r.json())}')
                    exit(1)
            else:
                print(f'Get {current_url} failed, code: {r.status_code}')
                exit(1)

