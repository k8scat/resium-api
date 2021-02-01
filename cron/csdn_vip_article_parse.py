# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/10/15

"""
import requests

if __name__ == '__main__':
    url = 'https://cms-api.csdn.net/v1/web_home/select_content'
    page = 1
    payload = {
        'componentIds': ['vip-blog'],
        'page': page
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
    }
    while True:
        print(f'当前页：{page}')
        with requests.post(url, headers=headers, json=payload) as r:
            if r.status_code == requests.codes.ok:
                print(f'Get {url} {r.status_code}')
                res = r.json()
                if res.get('code', 0) != 200:
                    print(f'请求CSDN获取VIP文章的接口失败, status_code={r.status_code}, content={r.text}')
                articles = res['data']['vip-blog']['data']
                for article in articles:
                    article_url = article['url']
                    check_payload = {
                        'token': 'csSM0Aw4NrvpZfxDEtbB3mPCWVUK52OnQik9djuLz1Ih8aToGJ',
                        'url': article_url
                    }
                    with requests.post('https://api.resium.ncucoder.com/check_article_existed/', json=check_payload) as check_res:
                        if check_res.status_code == requests.codes.ok:
                            res = check_res.json()
                            if res['code'] == requests.codes.ok:
                                if res['existed']:
                                    print(f'文章已存在，跳过：{article_url}')
                                    continue
                                else:
                                    parse_headers = {
                                        'Authorization': 'Bearer ' + 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI2NjY2NjYifQ.hcP4NzJUIigurnA0c1iXmE0H-kYaIogIz-iusKzf1jc1sL6VGm3ejnATQIPVNaB-oAWJSX1_KMKK9_KxvWCGvA'
                                    }
                                    parse_payload = {
                                        'url': article_url,
                                    }
                                    requests.post('https://api.resium.ncucoder.com/parse_csdn_article/',
                                                  headers=parse_headers,
                                                  data=parse_payload)
                                    print(f'文章解析请求发送成功：{article_url}')
                                    exit(0)
                        else:
                            print(f'接口请求失败：{check_res.status_code}')
            else:
                print(f'请求CSDN获取VIP文章的接口失败, status_code={r.status_code}, content={r.text}')
        page += 1
        payload['page'] = page
