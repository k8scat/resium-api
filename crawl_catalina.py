# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/20

"""
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()

import re
import uuid
import requests
from csdnbot.settings import base
from bs4 import BeautifulSoup
from downloader.utils import aliyun_oss_upload, get_file_md5, ding
from downloader.models import Resource


def parse_cookies():
    """
    解析cookies, 返回字典

    :return:
    """

    # 这个cookies直接从浏览器的network里复制过来就可以
    with open('catalina_cookies.txt', 'r') as f:
        cookies = f.read().replace(' ', '').split(';')
        cookies_dict = {}
        for cookie in cookies:
            cookie = cookie.split('=')
            cookies_dict.setdefault(cookie[0], cookie[1])

        return cookies_dict


def check_cookies():
    """
    检查cookies是否有效

    :return:
    """

    url = 'http://www.catalina.com.cn/u/setting'
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'host': 'www.catalina.com.cn',
        'referer': 'http://www.catalina.com.cn/u/hsowan/myhome',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36'
    }
    cookies = parse_cookies()
    account_username = 'hsowan'
    r = requests.get(url, headers=headers, cookies=cookies)
    if r.status_code == requests.codes.OK:
        if r.text.count(account_username):
            return True
        else:
            return False


def download(resource_id):
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
    cookies = parse_cookies()

    with requests.get(download_base_url + resource_id, headers=headers, cookies=cookies) as r:
        if r.status_code == requests.codes.OK:
            oss_url = r.content.decode()
            if re.match(r'^http://sheldonbucket\.oss-cn-shanghai\.aliyuncs\.com/.+', oss_url):
                with requests.get(oss_url, stream=True) as resp:
                    save_dir = os.path.join(base.DOWNLOAD_DIR, str(uuid.uuid1()))
                    os.mkdir(save_dir)
                    # 文件名
                    filename = str(resp.headers['Content-Disposition'].split('=')[1].encode('ISO-8859-1'), encoding='utf-8')
                    # 文件大小
                    size = int(resp.headers['Content-Length'])
                    # 文件存储路径
                    filepath = os.path.join(save_dir, filename)

                    chunk_size = 1024
                    write_count = 0
                    with open(filepath, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size):
                            f.write(chunk)
                            write_count += len(chunk)
                            print(f'{filename} 下载进度: {round(write_count/size*100, 2)}%')

                    return filename, size, filepath, save_dir


def parse_tags(resource_url):
    """
    获取资源标签

    :param resource_url:
    :return:
    """

    all_tags = []
    r = requests.get(resource_url)
    if r.status_code == requests.codes.OK:
        soup = BeautifulSoup(r.text, 'lxml')
        tags = soup.find('div', class_='divTags').find_all('span')
        for tag in tags:
            tag = tag.string.strip()
            if tag.count(' '):
                all_tags.extend(tag.split(' '))
            else:
                all_tags.append(tag)
        return all_tags
    else:
        ding('爬取Catalina: 获取资源标签失败')


def parse_resources():
    """
    爬取资源

    :return:
    """

    t = 2
    p = 1
    while True:
        if p == 1:
            # 资源分类
            url = f'http://www.catalina.com.cn/Access/c-{t}'
        else:
            # 分页
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
                        resource_url = f'http://www.catalina.com.cn/info_{resource_id}.html'
                        if Resource.objects.filter(url=resource_url).count():
                            print('资源已爬取, 跳过')
                            continue

                        title = content[1].string
                        desc = content[2].string
                        try:
                            filename, size, filepath, save_dir = download(resource_id)
                        except TypeError:
                            ding('爬取Catalina: 资源下载失败')
                            return

                        with open(filepath, 'rb') as f:
                            file_md5 = get_file_md5(f)
                            if Resource.objects.filter(file_md5=file_md5).count():
                                print('资源已存在, 跳过')
                                continue

                        tags = settings.TAG_SEP.join(parse_tags(resource_url))

                        key = f'{str(uuid.uuid1())}-{filename}'
                        if aliyun_oss_upload(filepath, key):
                            try:
                                Resource(title=title, desc=desc, filename=filename,
                                         size=size, file_md5=file_md5, category='移动开发-Android',
                                         tags=tags, key=key, download_count=0,
                                         user_id=1, url=resource_url).save()
                                ding(f'爬取Catalina: 资源创建成功: {filename}')
                            except Exception as e:
                                ding(f'爬取Catalina: 资源创建失败: {str(e)}')

                    finally:
                        if save_dir:
                            os.system(f'rm -rf {save_dir}')

            p += 1
        else:
            break


if __name__ == '__main__':
    parse_resources()
