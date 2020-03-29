# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/28

"""
import json
import logging
import os
import re
import uuid
from json import JSONDecodeError
from urllib import parse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.decorators import api_view
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from downloader.models import User, DownloadRecord, CsdnAccount, BaiduAccount, DocerAccount
from downloader.utils import check_oss, get_random_ua, ding, aliyun_oss_sign_url, save_resource, get_driver, \
    check_download


@api_view(['POST'])
def download(request):
    if request.method == 'POST':
        token = request.data.get('token', None)
        if not token or token != settings.BOT_TOKEN:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        qq = request.data.get('qq', None)
        url = request.data.get('url', None)
        if not qq or not url:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        if cache.get(str(qq)):
            return JsonResponse(dict(code=403, msg='下载请求过快'))

        try:
            user = User.objects.get(qq=qq, is_active=True)
            cache.set(str(qq), True, timeout=settings.COOLQ_DOWNLOAD_INTERVAL)
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='请先绑定源自下载账号'))

        # 检查OSS是否存有该资源
        oss_resource = check_oss(url)
        if oss_resource:
            # CSDN资源
            if re.match(settings.PATTERN_CSDN, url):
                point = settings.CSDN_POINT

            # 百度文库文档
            elif re.match(settings.PATTERN_WENKU, url):
                if oss_resource.wenku_type == 'VIP免费文档':
                    point = settings.WENKU_VIP_FREE_DOC_POINT
                elif oss_resource.wenku_type == 'VIP专享文档':
                    point = settings.WENKU_SPECIAL_DOC_POINT
                elif oss_resource.wenku_type == '共享文档':
                    point = settings.WENKU_SHARE_DOC_POINT
                else:
                    ding('[百度文库] 已有百度文库文档的类型获取失败',
                         resource_url=url,
                         qq=qq)
                    return JsonResponse(dict(code=500, msg='资源获取失败'))

            # 稻壳模板
            elif re.match(settings.PATTERN_DOCER, url):
                point = settings.DOCER_POINT

            elif re.match(settings.PATTERN_ZHIWANG, url):
                point = settings.ZHIWANG_POINT

            else:
                return JsonResponse(dict(code=400, msg='无效的资源地址'))

            if user.point < point:
                return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

            # 判断用户是否下载过该资源
            # 若没有，则给上传资源的用户赠送积分
            if user != oss_resource.user:
                if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
                    oss_resource.user.point += 1
                    oss_resource.user.save()

            # 新增下载记录
            DownloadRecord(user=user,
                           resource=oss_resource,
                           download_device=user.login_device,
                           download_ip=user.login_ip,
                           used_point=point).save()
            # 更新用户积分
            user.point -= point
            user.used_point += point
            user.save()

            # 生成临时下载地址
            download_url = aliyun_oss_sign_url(oss_resource.key)

            # 更新资源的下载次数
            oss_resource.download_count += 1
            oss_resource.save()

            return JsonResponse(dict(code=200, download_url=download_url))

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
        # 将资源存放的路径记录到日志
        logging.info(f'资源[{url}]保存路径: {save_dir}')

        # CSDN资源下载
        if re.match(settings.PATTERN_CSDN, url):
            logging.info(f'CSDN 资源下载: {url}')
            try:
                csdn_account = CsdnAccount.objects.get(is_enabled=True)
                # 如果不是我的csdn账号或者账号当天下载数超过10，则将积分上调
                point = settings.CSDN_POINT
                # 可用积分不足
                if user.point < point:
                    return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

                # 判断账号当天下载数
                if csdn_account.today_download_count >= 20:
                    ding(f'[CSDN] 今日下载数已用完',
                         qq=qq,
                         resource_url=url,
                         used_account=csdn_account)
                    return JsonResponse(dict(code=403, msg='下载失败'))
            except CsdnAccount.DoesNotExist:
                ding('[CSDN] 没有可用账号',
                     qq=qq,
                     resource_url=url)
                return JsonResponse(dict(code=400, msg='下载失败'))

            with requests.get(url) as r:
                soup = BeautifulSoup(r.text, 'lxml')
                # 版权受限，无法下载
                # https://download.csdn.net/download/c_baby123/10791185
                cannot_download = len(soup.select('div.resource_box a.copty-btn'))
                if cannot_download:
                    ding('[CSDN] 用户尝试下载版权受限的资源',
                         qq=qq,
                         resource_url=url)
                    return JsonResponse(dict(code=400, msg='版权受限，无法下载'))
                # 获取资源标题
                title = soup.select('div.resource_box_info span.resource_title')[0].string
                desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
                tags = settings.TAG_SEP.join(
                    [tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')])

            resource_id = url.split('/')[-1]
            headers = {
                'cookie': csdn_account.cookies,
                'user-agent': get_random_ua(),
                'referer': url  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
            }
            with requests.get(f'https://download.csdn.net/source/download?source_id={resource_id}',
                              headers=headers) as r:
                try:
                    resp = r.json()
                except JSONDecodeError:
                    ding('[CSDN] 下载失败',
                         error=r.text,
                         resource_url=url,
                         qq=qq,
                         used_account=csdn_account.email,
                         logger=logging.error)
                    return JsonResponse(dict(code=500, msg='下载失败'))
                if resp['code'] == 200:
                    # 更新账号今日下载数
                    csdn_account.today_download_count += 1
                    csdn_account.used_count += 1
                    csdn_account.save()

                    # 更新用户的剩余积分和已用积分
                    user.point -= point
                    user.used_point += point
                    user.save()

                    with requests.get(resp['data'], headers=headers, stream=True) as download_resp:
                        if download_resp.status_code == requests.codes.OK:
                            filename = parse.unquote(download_resp.headers['Content-Disposition'].split('"')[1])
                            filepath = os.path.join(save_dir, filename)
                            # 写入文件，用于线程上传资源到OSS
                            with open(filepath, 'wb') as f:
                                for chunk in download_resp.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                            # 上传资源到OSS并保存记录到数据库
                            download_url = save_resource(url, filename, filepath, title, tags, desc, point, user,
                                                         account=csdn_account, ret=True)
                            return JsonResponse(dict(code=200, download_url=download_url))

                        ding('[CSDN] 下载失败',
                             error=download_resp.text,
                             qq=qq,
                             resource_url=url,
                             used_account=csdn_account.email,
                             logger=logging.error)
                        return JsonResponse(dict(code=500, msg='下载失败'))
                else:
                    if resp.get('message', None) == '当前资源不开放下载功能':
                        return JsonResponse(dict(code=400, msg='CSDN未开放该资源的下载功能'))

                    ding('[CSDN] 下载失败',
                         error=resp,
                         qq=qq,
                         resource_url=url,
                         used_account=csdn_account.email,
                         logger=logging.error)
                    return JsonResponse(dict(code=400, msg='下载失败'))

        # 百度文库文档下载
        elif re.match(settings.PATTERN_WENKU, url):
            logging.info(f'百度文库资源下载: {url}')

            driver = get_driver(unique_folder)
            try:
                baidu_account = BaiduAccount.objects.get(is_enabled=True)
            except BaiduAccount.DoesNotExist:
                ding('没有可用的百度文库账号',
                     qq=qq,
                     resource_url=url)
                return JsonResponse(dict(code=500, msg='下载失败'))

            try:
                driver.get('https://www.baidu.com/')
                # 添加cookies
                cookies = json.loads(baidu_account.cookies)
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    driver.add_cookie(cookie)
                driver.get(url)
                try:
                    # 获取百度文库文档类型
                    doc_type = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                                                        "//div[@class='doc-tag-wrap super-vip']/div[contains(@style, 'block')]/span"))
                    ).text
                    logging.info(doc_type)
                except TimeoutException:
                    ding('[百度文库] 文档类型获取失败',
                         used_account=baidu_account.email,
                         resource_url=url,
                         qq=qq,
                         logger=logging.error)
                    return JsonResponse(dict(code=500, msg='下载失败'))

                soup = BeautifulSoup(driver.page_source, 'lxml')
                desc = soup.select('span.doc-desc-all')
                title = soup.select('span.doc-header-title')[0].text
                tags = settings.TAG_SEP.join([tag.text for tag in soup.select('div.tag-tips a')])
                desc = desc[0].text.strip() if desc else ''

                if doc_type == 'VIP免费文档':
                    point = settings.WENKU_VIP_FREE_DOC_POINT
                    baidu_account.vip_free_count += 1
                elif doc_type == '共享文档':
                    point = settings.WENKU_SHARE_DOC_POINT
                    baidu_account.share_doc_count += 1
                elif doc_type == 'VIP专项文档':
                    point = settings.WENKU_SPECIAL_DOC_POINT
                    baidu_account.special_doc_count += 1
                else:
                    ding(f'[百度文库] 用户尝试下载不支持的文档：{doc_type}',
                         qq=qq,
                         resource_url=url)
                    return JsonResponse(dict(code=400, msg='此类资源无法下载: ' + doc_type))

                if user.point < point:
                    return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))
                # 更新用户积分
                user.point -= point
                user.used_point += point
                user.save()
                baidu_account.save()

                # 显示下载对话框的按钮
                show_download_modal_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.reader-download.btn-download'))
                )
                show_download_modal_button.click()
                # 下载按钮
                try:
                    # 首次下载
                    download_button = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'div.dialog-inner.tac > a.ui-bz-btn-senior.btn-diaolog-downdoc'))
                    )
                    # 取消转存网盘
                    cancel_wp_upload_check = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.wpUpload input'))
                    )
                    cancel_wp_upload_check.click()
                    download_button.click()
                except TimeoutException:
                    if doc_type != 'VIP专享文档':
                        # 已转存过此文档
                        download_button = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'WkDialogOk'))
                        )
                        download_button.click()
                    else:
                        ding('百度文库下载失败',
                             qq=qq,
                             used_account=baidu_account.email,
                             resource_url=url,
                             logger=logging.error)
                        return JsonResponse(dict(code=500, msg='下载失败'))

                filepath, filename = check_download(save_dir)
                # 保存资源
                download_url = save_resource(url, filename, filepath, title, tags, desc, point, user,
                                             account=baidu_account, wenku_type=doc_type, ret=True)

                return JsonResponse(dict(code=200, download_url=download_url))

            except Exception as e:
                ding('[百度文库] 下载失败',
                     error=e,
                     qq=qq,
                     used_account=baidu_account.email,
                     resource_url=url)
                return JsonResponse(dict(code=500, msg='下载失败'))

            finally:
                driver.quit()

        # 稻壳模板下载
        elif re.match(settings.PATTERN_DOCER, url):
            logging.info(f'稻壳模板下载: {url}')

            if user.point < settings.DOCER_POINT:
                return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

            try:
                docer_account = DocerAccount.objects.get(is_enabled=True)
            except DocerAccount.DoesNotExist:
                ding('没有可以使用的稻壳VIP模板账号',
                     qq=qq,
                     resource_url=url)
                return JsonResponse(dict(code=500, msg='下载失败'))

            # 爬取资源的信息
            with requests.get(url) as r:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('h1', class_='preview__title').string
                tags = [tag.text for tag in soup.select('li.preview__labels-item.g-link a')]
                if '展开更多' in tags:
                    tags = tags[:-1]
                tags = settings.TAG_SEP.join(tags)
                # 从head中获取desc
                desc = soup.find('meta', attrs={'name': 'Description'})['content']
                is_docer_vip_doc = r.text.count('类型：VIP模板') > 0

            # 下载资源
            resource_id = url.split('/')[-1]
            parse_url = f'https://www.docer.com/detail/dl?id={resource_id}'
            headers = {
                'cookie': docer_account.cookies,
                'user-agent': get_random_ua()
            }
            # 如果cookies失效，r.json()会抛出异常
            with requests.get(parse_url, headers=headers) as r:
                try:
                    resp = r.json()
                    if resp['result'] == 'ok':
                        # 更新用户积分
                        point = settings.DOCER_POINT
                        user.point -= point
                        user.used_point += point
                        user.save()

                        # 更新账号使用下载数
                        docer_account.used_count += 1
                        docer_account.save()

                        download_url = resp['data']
                        filename = download_url.split('/')[-1]
                        filepath = os.path.join(save_dir, filename)
                        with requests.get(download_url, stream=True) as download_resp:
                            if download_resp.status_code == requests.codes.OK:
                                with open(filepath, 'wb') as f:
                                    for chunk in download_resp.iter_content(chunk_size=1024):
                                        if chunk:
                                            f.write(chunk)

                                # 保存资源
                                download_url = save_resource(url, filename, filepath, title, tags, desc, point, user,
                                                             account=docer_account, is_docer_vip_doc=is_docer_vip_doc, ret=True)

                                return JsonResponse(dict(code=200, download_url=download_url))

                            ding('[稻壳VIP模板] 下载失败',
                                 error=download_resp.text,
                                 qq=qq,
                                 used_account=docer_account.email,
                                 resource_url=url,
                                 logger=logging.error)
                            return JsonResponse(dict(code=500, msg='下载失败'))
                    else:
                        ding('[稻壳VIP模板] 下载失败',
                             error=r.text,
                             qq=qq,
                             resource_url=url,
                             logger=logging.error)
                        return JsonResponse(dict(code=500, msg='下载失败'))
                except JSONDecodeError:
                    ding('[稻壳VIP模板] Cookies失效',
                         user_email=user.email,
                         resource_url=url,
                         logger=logging.error)
                    return JsonResponse(dict(code=500, msg='下载失败'))

        elif re.match(settings.PATTERN_ZHIWANG, url):
            return JsonResponse(dict(code=400, msg='暂不支持下载知网文献'))

        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))
