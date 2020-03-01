# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/20

爬取Catalina站点资源并上传至OSS

"""
import logging
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


def parse_types():
    """
    解析出不同类别资源的地址

    :return: generator
    """
    url = 'http://www.catalina.com.cn/'
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'connection': 'keep-alive',
        'host': 'www.catalina.com.cn',
        'referer': 'http://www.catalina.com.cn/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36'
    }
    with requests.get(url, headers=headers) as r:
        if r.status_code == requests.codes.OK:
            soup = BeautifulSoup(r.text, 'lxml')
            items = soup.select('div.cate-menu')
            for item in items:
                # 所有分类
                all_classes = item.select('a')
                # 一级分类
                top_class = all_classes[0].text
                # 二级分类
                # tag数组, 获取字符串: tag.text, 获取href: tag['href']
                sub_classes = all_classes[1:]
                yield top_class, sub_classes


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

    logging.info('cookies无效')
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
            logging.info(f'OSS 地址: {oss_url}')
            if re.match(r'^http://sheldonbucket\.oss-cn-shanghai\.aliyuncs\.com/.+', oss_url):
                with requests.get(oss_url, stream=True) as resp:
                    save_dir = os.path.join(base.DOWNLOAD_DIR, str(uuid.uuid1()))
                    os.mkdir(save_dir)

                    try:
                        # 文件名
                        # 解决中文编码问题
                        # 'è¯­é³è¯å«åèçè¿æ¥mainactivity .java.txt'.encode('ISO-8859-1').decode('utf-8')
                        filename = str(resp.headers['Content-Disposition'].split('=')[1].encode('ISO-8859-1'),
                                       encoding='utf-8')
                    except KeyError:
                        filename = oss_url.split('?')[0].split('http://sheldonbucket.oss-cn-shanghai.aliyuncs.com/')[1]
                    # 解决无法创建文件的问题: 微信小插件 支持（聊天纪录/微信多开/防撤回/红包提醒）.zip
                    filename.replace('/', '-')
                    filename.replace(' ', '-')
                    logging.info(f'文件名: {filename}')

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
                            # logging.info(f'{filename} 下载进度: {round(write_count / size * 100, 2)}%')

                    return filename, size, filepath, save_dir

        else:
            if r.text.count('远程服务器返回错误: (404) 未找到。'):
                return 404
            else:
                return False


def parse_tags(resource_url):
    """
    获取资源标签

    :param resource_url:
    :return:
    """

    with requests.get(resource_url) as r:
        all_tags = []
        if r.status_code == requests.codes.OK:
            # 进一步检测是否是免费下载资源
            if r.text.count('所需积分'):
                return '非免费下载资源'

            soup = BeautifulSoup(r.text, 'lxml')
            tags = soup.find('div', class_='divTags').find_all('span')
            for tag in tags:
                tag = tag.string.strip()
                if tag.count(' '):
                    all_tags.extend(tag.split(' '))
                else:
                    all_tags.append(tag)
            return settings.TAG_SEP.join(all_tags)
        else:
            return '获取资源标签失败'


def parse_resources():
    """
    爬取资源

    :return:
    """

    for top_class, sub_classes in parse_types():
        for sub_class in sub_classes:
            category = f'{top_class}-{sub_class.text}'
            t = sub_class['href'].split('-')[1]
            p = 1
            while True:
                if p == 1:
                    # 资源分类
                    url = f'http://www.catalina.com.cn/Access/c-{t}'
                    ding(f'开始爬取: {url}')
                else:
                    # 分页
                    url = f'http://www.catalina.com.cn/Access/cp-{t}-{p}'
                with requests.get(url) as r:
                    if r.status_code == requests.codes.OK:
                        soup = BeautifulSoup(r.text, 'lxml')
                        items = soup.find('ul', class_='list-unstyled jh-library-item').find_all('li', recursive=False)
                        if len(items) <= 0:
                            break
                        for item in items:
                            content = item.find_all('a')
                            if content[0].string == '【免费】':
                                save_dir = None
                                try:
                                    resource_id = re.findall(r'\d+', content[1]['href'])[0]
                                    resource_url = f'http://www.catalina.com.cn/info_{resource_id}.html'
                                    logging.info(f'资源地址: {resource_url} in {url}')
                                    if Resource.objects.filter(url=resource_url).count():
                                        logging.info('资源已爬取, 跳过')
                                        continue

                                    tags = parse_tags(resource_url)
                                    if tags == '获取资源标签失败':
                                        ding(f'爬取Catalina: 获取资源标签失败 {resource_url}, 资源所处位置: {url}')
                                        return
                                    if tags == '非免费下载资源':
                                        continue
                                    title = content[1].string
                                    desc = content[2].string

                                    download_result = download(resource_id)
                                    if download_result == 404:
                                        logging.info('该资源不可下载: 404')
                                        continue
                                    elif download_result is False:
                                        ding(f'爬取Catalina: 资源下载失败 {resource_url}, 资源所处位置: {url}')
                                        return
                                    else:
                                        filename, size, filepath, save_dir = download_result

                                    with open(filepath, 'rb') as f:
                                        file_md5 = get_file_md5(f)
                                        if Resource.objects.filter(file_md5=file_md5).count():
                                            logging.info('资源已存在, 跳过')
                                            continue

                                    key = f'{str(uuid.uuid1())}-{filename}'
                                    if aliyun_oss_upload(filepath, key):
                                        try:
                                            Resource(title=title, desc=desc, filename=filename,
                                                     size=size, file_md5=file_md5, category=category,
                                                     tags=tags, key=key, download_count=0,
                                                     user_id=1, url=resource_url).save()
                                            ding(f'爬取Catalina: 资源创建成功: {filename}')
                                        except Exception as e:
                                            logging.error(e)
                                            ding(f'爬取Catalina: 资源创建失败: {str(e)}, 资源地址: {resource_url}, 资源所处位置: {url}')

                                except Exception as e:
                                    logging.error(e)
                                    ding(f'爬取Catalina: 出现未知异常 {str(e)}')

                                finally:
                                    if save_dir:
                                        os.system(f'rm -rf {save_dir}')

                        p += 1
                    else:
                        ding(f'资源请求失败: {url}')
                        return


if __name__ == '__main__':
    if check_cookies():
        parse_resources()
