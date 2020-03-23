# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
import json
import logging
import os
import random
import re
import string
import uuid
from json import JSONDecodeError
from threading import Thread
from urllib import parse

import requests
from PIL import Image
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse, FileResponse
from ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.decorators import auth
from downloader.models import Resource, User, ResourceComment, DownloadRecord, CsdnAccount, DocerAccount, BaiduAccount, \
    DocerPreviewImage
from downloader.serializers import ResourceSerializers, ResourceCommentSerializers
from downloader.utils import aliyun_oss_upload, get_file_md5, ding, aliyun_oss_sign_url, \
    check_download, get_driver, check_oss, aliyun_oss_check_file, \
    save_resource, send_email, predict_code, get_random_ua


@auth
@api_view(['POST'])
def upload(request):
    if request.method == 'POST':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
            if not user.phone:
                return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        file = request.FILES.get('file', None)
        if not file:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        # 向上扩大10MiB
        if file.size > (2 * 100 + 10) * 1024 * 1024:
            return JsonResponse(dict(code=400, msg='上传资源大小不能超过200MiB'))

        file_md5 = get_file_md5(file.open('rb'))
        if Resource.objects.filter(file_md5=file_md5).count():
            return JsonResponse(dict(code=400, msg='资源已存在'))

        data = request.POST
        title = data.get('title', None)
        tags = data.get('tags', None)
        desc = data.get('desc', None)
        category = data.get('category', None)
        if title and tags and desc and category and file:
            try:
                filename = file.name
                key = f'{str(uuid.uuid1())}-{filename}'
                logging.info(f'Upload resource: {key}')
                filepath = os.path.join(settings.UPLOAD_DIR, key)
                # 写入文件，之后使用线程进行上传
                with open(filepath, 'wb') as f:
                    for chunk in file.chunks():
                        f.write(chunk)
                Resource(title=title, desc=desc, tags=tags,
                         category=category, filename=filename, size=file.size,
                         download_count=0, is_audited=0, key=key,
                         user=user, file_md5=file_md5).save()

                # 开线程上传资源到OSS
                t = Thread(target=aliyun_oss_upload, args=(filepath, key))
                t.start()

                # 发送邮件通知
                subject = '[源自下载] 资源上传成功'
                content = '您上传的资源将由管理员审核。如果审核通过，当其他用户下载该资源时，您将获得1积分奖励。'
                send_email(subject, content, user.email)

                ding(f'有新的资源上传 {key}')
                return JsonResponse(dict(code=200, msg='资源上传成功'))
            except Exception as e:
                logging.error(e)
                ding(f'资源上传失败: {str(e)}')
                return JsonResponse(dict(code=500, msg='资源上传失败'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def check_file(request):
    """
    根据md5值判断资源是否存在

    :param request:
    :return:
    """

    if request.method == 'GET':
        file_md5 = request.GET.get('hash', None)
        if Resource.objects.filter(file_md5=file_md5).count():
            return JsonResponse(dict(code=400, msg='资源已存在'))
        return JsonResponse(dict(code=200, msg='资源不存在'))


@auth
@api_view(['GET'])
def list_uploaded_resources(request):
    """
    获取用户上传资源

    :param request:
    :return:
    """

    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email)
            resources = Resource.objects.order_by('-create_time').filter(user=user).all()
            return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))
        except User.DoesNotExist:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def get_resource(request):
    if request.method == 'GET':
        resource_id = request.GET.get('id', None)
        if resource_id:
            try:
                resource = Resource.objects.get(id=resource_id, is_audited=1)
                preview_images = []
                if re.match(r'^(http(s)?://www\.docer\.com/(webmall/)?preview/).+$', resource.url):
                    preview_images = [
                        {
                            'url': preview_image.url,
                            'alt': preview_image.alt
                        } for preview_image in DocerPreviewImage.objects.filter(resource_url=resource.url).all()
                    ]
                resource = ResourceSerializers(resource).data
                resource.setdefault('preview_images', preview_images)
                return JsonResponse(dict(code=200, resource=resource))
            except Resource.DoesNotExist:
                return JsonResponse(dict(code=404, msg='资源不存在'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def list_comments(request):
    if request.method == 'GET':
        resource_id = request.GET.get('resource_id', None)
        if resource_id:
            try:
                comments = ResourceComment.objects.filter(resource_id=resource_id).all()
                return JsonResponse(dict(code=200, comments=ResourceCommentSerializers(comments, many=True).data))
            except Resource.DoesNotExist:
                return JsonResponse(dict(code=404, msg='资源不存在'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@ratelimit(key='ip', rate='1/5m', block=True)
@auth
@api_view(['POST'])
def create_comment(request):
    if request.method == 'POST':
        content = request.data.get('content', None)
        resource_id = request.data.get('resource_id', None)
        user_id = request.data.get('user_id', None)
        if content and resource_id and user_id:
            try:
                resource = Resource.objects.get(id=resource_id, is_audited=1)
                user = User.objects.get(id=user_id)
                ResourceComment(user=user, resource=resource, content=content).save()
                return JsonResponse(dict(code=200, msg='评论成功'))
            except (User.DoesNotExist, Resource.DoesNotExist):
                return JsonResponse(dict(code=400, msg='错误的请求'))
        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@auth
@api_view(['GET'])
def list_resources(request):
    """
    分页获取资源
    """
    if request.method == 'GET':
        page = int(request.GET.get('page', 1))
        count = int(request.GET.get('count', 5))
        key = request.GET.get('key', '')
        if page < 1:
            page = 1

        start = count * (page - 1)
        end = start + count
        # https://cloud.tencent.com/developer/ask/81558
        resources = Resource.objects.order_by('-create_time').filter(Q(is_audited=1),
                                                                     Q(title__icontains=key) |
                                                                     Q(desc__icontains=key) |
                                                                     Q(tags__icontains=key)).all()[start:end]
        return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))


@auth
@api_view(['GET'])
def get_resource_count(request):
    """
    获取资源的数量
    """
    if request.method == 'GET':
        key = request.GET.get('key', '')
        return JsonResponse(dict(code=200, count=Resource.objects.filter(Q(is_audited=1),
                                                                         Q(title__icontains=key) |
                                                                         Q(desc__icontains=key) |
                                                                         Q(tags__icontains=key)).count()))


@auth
@api_view(['GET'])
def list_resource_tags(request):
    """
    获取所有的资源标签
    """
    if request.method == 'GET':
        tags = Resource.objects.values_list('tags')
        ret_tags = []
        for tag in tags:
            for t in tag[0].split(settings.TAG_SEP):
                if t not in ret_tags and t != '':
                    ret_tags.append(t)

        return JsonResponse(dict(code=200, tags=settings.TAG_SEP.join(random.sample(ret_tags, settings.SAMPLE_TAG_COUNT))))


@ratelimit(key='ip', rate='1/m', block=settings.RATELIMIT_BLOCK)
@auth
@api_view(['POST'])
def download(request):
    """
    资源下载
    """
    if request.method == 'POST':
        email = request.session.get('email')
        if cache.get(email):
            return JsonResponse(dict(code=403, msg='下载请求过快'), status=403)

        try:
            user = User.objects.get(email=email, is_active=True)
            if not user.phone:
                return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))

            cache.set(email, True, timeout=settings.DOWNLOAD_INTERVAL)
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        resource_url = request.data.get('url', None)
        if not resource_url:
            return JsonResponse(dict(code=400, msg='资源地址不能为空'))
        if not re.match(r'^(http(s)?://kns\.cnki\.net/KCMS/detail/).+$', resource_url):
            # 去除资源地址参数
            resource_url = resource_url.split('?')[0]

        download_type = request.data.get('dt', None)
        # 检查OSS是否存有该资源
        oss_resource = check_oss(resource_url, download_type)
        if oss_resource:
            point = request.data.get('point')
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
            url = aliyun_oss_sign_url(oss_resource.key)

            # 更新资源的下载次数
            oss_resource.download_count += 1
            oss_resource.save()

            return JsonResponse(dict(code=200, url=url))

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

        # CSDN资源下载
        if re.match(r'^(http(s)?://download\.csdn\.net/download/).+$', resource_url):
            logging.info(f'CSDN 资源下载: {resource_url}')

            # 可用积分不足
            if user.point < settings.CSDN_POINT:
                return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

            try:
                csdn_account = CsdnAccount.objects.get(is_enabled=True)
                # 判断账号当天下载数
                if csdn_account.today_download_count >= 20:
                    ding(f'[CSDN] 今日下载数已用完',
                         at_mobiles=['17770040362'],
                         user_email=email,
                         resource_url=resource_url,
                         used_account=csdn_account)
                    return JsonResponse(dict(code=403, msg='下载失败'))
            except CsdnAccount.DoesNotExist:
                ding('[CSDN] 没有可用账号',
                     user_email=email,
                     resource_url=resource_url)
                return JsonResponse(dict(code=400, msg='下载失败'))

            with requests.get(resource_url) as r:
                soup = BeautifulSoup(r.text, 'lxml')
                # 版权受限，无法下载
                # https://download.csdn.net/download/c_baby123/10791185
                cannot_download = len(soup.select('div.resource_box a.copty-btn'))
                if cannot_download:
                    ding('[CSDN] 用户尝试下载版权受限的资源',
                         user_email=user.email,
                         resource_url=resource_url)
                    return JsonResponse(dict(code=400, msg='版权受限，无法下载'))
                # 获取资源标题
                title = soup.select('div.resource_box_info span.resource_title')[0].string
                desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
                tags = settings.TAG_SEP.join(
                    [tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')])

            resource_id = resource_url.split('/')[-1]
            headers = {
                'cookie': csdn_account.cookies,
                'user-agent': get_random_ua(),
                'referer': resource_url  # OSS下载时需要这个请求头，获取资源下载链接时可以不需要
            }
            with requests.get(f'https://download.csdn.net/source/download?source_id={resource_id}',
                              headers=headers) as r:
                try:
                    resp = r.json()
                except JSONDecodeError:
                    ding('[CSDN] 下载失败',
                         error=r.text,
                         resource_url=resource_url,
                         user_email=user.email,
                         used_account=csdn_account.email,
                         logger=logging.error)
                    return JsonResponse(dict(code=500, msg='下载失败'))
                if resp['code'] == 200:
                    # 更新账号今日下载数
                    csdn_account.today_download_count += 1
                    csdn_account.used_count += 1
                    csdn_account.save()

                    # 更新用户的剩余积分和已用积分
                    point = settings.CSDN_POINT
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
                            t = Thread(target=save_resource,
                                       args=(resource_url, filename, filepath, title, tags, desc, point, user),
                                       kwargs={'account': csdn_account})
                            t.start()

                            response = FileResponse(open(filepath, 'rb'))
                            response['Content-Type'] = 'application/octet-stream'
                            # 'attachment;filename="' + parse.quote(filename, safe=string.printable) + '"'
                            response['Content-Disposition'] = download_resp.headers['Content-Disposition']
                            return response

                        ding('[CSDN] 下载失败',
                             error=download_resp.text,
                             user_email=email,
                             resource_url=resource_url,
                             used_account=csdn_account.email,
                             logger=logging.error)
                        return JsonResponse(dict(code=500, msg='下载失败'))
                else:
                    if resp.get('message', None) == '当前资源不开放下载功能':
                        return JsonResponse(dict(code=400, msg='CSDN未开放该资源的下载功能'))

                    ding('[CSDN] 下载失败',
                         error=resp,
                         user_email=email,
                         resource_url=resource_url,
                         used_account=csdn_account.email,
                         logger=logging.error)
                    return JsonResponse(dict(code=400, msg='下载失败'))

        # 百度文库文档下载
        elif re.match(r'^(http(s)?://wenku\.baidu\.com/view/).+$', resource_url):
            logging.info(f'百度文库资源下载: {resource_url}')

            driver = get_driver(unique_folder)
            try:
                baidu_account = BaiduAccount.objects.get(is_enabled=True)
            except BaiduAccount.DoesNotExist:
                ding('没有可用的百度文库账号',
                     user_email=email,
                     resource_url=resource_url)
                return JsonResponse(dict(code=500, msg='下载失败'))

            try:
                driver.get('https://www.baidu.com/')
                # 添加cookies
                cookies = json.loads(baidu_account.cookies)
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    driver.add_cookie(cookie)
                driver.get(resource_url)
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
                         resource_url=resource_url,
                         user_email=email,
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
                         user_email=email,
                         resource_url=resource_url)
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
                             user_email=email,
                             used_account=baidu_account.email,
                             resource_url=resource_url,
                             logger=logging.error)
                        return JsonResponse(dict(code=500, msg='下载失败'))

                filepath, filename = check_download(save_dir)
                # 保存资源
                t = Thread(target=save_resource,
                           args=(resource_url, filename, filepath, title, tags, desc, point, user),
                           kwargs={'account': baidu_account, 'wenku_type': doc_type})
                t.start()

                response = FileResponse(open(filepath, 'rb'))
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                        safe=string.printable) + '"'

                return response

            except Exception as e:
                ding('[百度文库] 下载失败',
                     error=e,
                     user_email=email,
                     used_account=baidu_account.email,
                     resource_url=resource_url)
                return JsonResponse(dict(code=500, msg='下载失败'))

            finally:
                driver.quit()

        # 稻壳模板下载
        elif re.match(r'^(http(s)?://www\.docer\.com/(webmall/)?preview/).+$', resource_url):
            logging.info(f'稻壳模板下载: {resource_url}')

            if user.point < settings.DOCER_POINT:
                return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

            try:
                docer_account = DocerAccount.objects.get(is_enabled=True)
            except DocerAccount.DoesNotExist:
                ding('没有可以使用的稻壳VIP模板账号',
                     user_email=email,
                     resource_url=resource_url)
                return JsonResponse(dict(code=500, msg='下载失败'))

            # 爬取资源的信息
            with requests.get(resource_url) as r:
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
            resource_id = resource_url.split('/')[-1]
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
                                t = Thread(target=save_resource,
                                           args=(resource_url, filename, filepath, title, tags, desc, point, user),
                                           kwargs={'account': docer_account, 'is_docer_vip_doc': is_docer_vip_doc})
                                t.start()

                                response = FileResponse(open(filepath, 'rb'))
                                response['Content-Type'] = 'application/octet-stream'
                                response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                                        safe=string.printable) + '"'

                                return response

                            ding('[稻壳VIP模板] 下载失败',
                                 error=download_resp.text,
                                 user_email=user.email,
                                 used_account=docer_account.email,
                                 resource_url=resource_url,
                                 logger=logging.error)
                            return JsonResponse(dict(code=500, msg='下载失败'))
                    else:
                        ding('[稻壳VIP模板] 下载失败',
                             error=r.text,
                             user_email=user.email,
                             resource_url=resource_url,
                             logger=logging.error)
                        return JsonResponse(dict(code=500, msg='下载失败'))
                except JSONDecodeError:
                    ding('[稻壳VIP模板] Cookies失效',
                         user_email=user.email,
                         resource_url=resource_url,
                         logger=logging.error)
                    return JsonResponse(dict(code=500, msg='下载失败'))

        # 知网下载
        # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
        # https://kns.cnki.net/KCMS/detail/ 官网
        elif re.match(r'^(http(s)?://kns\.cnki\.net/KCMS/detail/).+$', resource_url):

            point = settings.ZHIWANG_POINT
            if user.point < point:
                return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))

            if not download_type:
                return JsonResponse(dict(code=400, msg='错误的请求'))

            # url = resource_url.replace('https://kns.cnki.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn')
            url = re.sub(r'http(s)?://kns\.cnki\.net', 'http://kns-cnki-net.wvpn.ncu.edu.cn', resource_url)
            driver = get_driver(unique_folder, load_images=True)
            try:
                driver.get('http://wvpn.ncu.edu.cn/users/sign_in')
                username_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, 'user_login'))
                )
                username_input.send_keys(settings.NCU_VPN_USERNAME)
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, 'user_password'))
                )
                password_input.send_keys(settings.NCU_VPN_PASSWORD)
                submit_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@class='col-md-6 col-md-offset-6 login-btn']/input")
                    )
                )
                submit_button.click()

                driver.get(url)
                driver.refresh()

                # 文献标题
                title = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@class='wxTitle']/h2")
                    )
                ).text

                # 尝试获取摘要
                try:
                    desc = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located(
                            (By.ID, 'ChDivSummary')
                        )
                    ).text
                except TimeoutException:
                    desc = ''

                # 尝试获取关键词
                try:
                    # //div[@class='wxBaseinfo']//label[@id='catalog_KEYWORD']/../a
                    items = WebDriverWait(driver, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, "//div[@class='wxBaseinfo']//label[@id='catalog_KEYWORD']/../a")
                        )
                    )
                    tags = []
                    for item in items:
                        tags.append(item.text[:-1])
                    tags = settings.TAG_SEP.join(tags)
                except TimeoutException:
                    tags = ''

                # 获取下载按钮
                if download_type == 'caj':
                    # caj下载
                    download_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, 'cajDown')
                        )
                    )
                elif download_type == 'pdf':
                    # pdf下载
                    download_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, 'pdfDown')
                        )
                    )
                else:
                    return JsonResponse(dict(code=400, msg='错误的请求'))
                # 获取下载链接
                download_link = download_button.get_attribute('href')
                # 访问下载链接
                driver.get(download_link)
                try:
                    # 获取验证码图片
                    code_image = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located(
                            (By.ID, 'vImg')
                        )
                    )
                    # 自动获取截取位置
                    # left = int(code_image.location['x'])
                    # print(left)
                    # upper = int(code_image.location['y'])
                    # print(upper)
                    # right = int(code_image.location['x'] + code_image.size['width'])
                    # print(right)
                    # lower = int(code_image.location['y'] + code_image.size['height'])
                    # print(lower)

                    # 获取截图
                    driver.get_screenshot_as_file(settings.SCREENSHOT_IMAGE)

                    # 手动设置截取位置
                    left = 430
                    upper = 275
                    right = 620
                    lower = 340
                    # 通过Image处理图像
                    img = Image.open(settings.SCREENSHOT_IMAGE)
                    # 剪切图片
                    img = img.crop((left, upper, right, lower))
                    # 保存剪切好的图片
                    img.save(settings.CODE_IMAGE)

                    code = predict_code(settings.CODE_IMAGE)
                    if code:
                        code_input = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.ID, 'vcode')
                            )
                        )
                        code_input.send_keys(code)
                        submit_code_button = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//dl[@class='c_verify-code']/dd/button")
                            )
                        )
                        submit_code_button.click()
                    else:
                        return JsonResponse(dict(code=500, msg='下载失败'))

                finally:
                    logging.info(save_dir)
                    filepath, filename = check_download(save_dir)

                    # 保存资源
                    t = Thread(target=save_resource,
                               args=(resource_url, filename, filepath, title, tags, desc, point, user),
                               kwargs={'zhiwang_type': download_type})
                    t.start()

                    user.point -= point
                    user.used_point += point
                    user.save()

                    response = FileResponse(open(filepath, 'rb'))
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                            safe=string.printable) + '"'
                    return response

            except Exception as e:
                ding('[知网文献] 下载失败',
                     error=e,
                     user_email=user.email,
                     resource_url=resource_url,
                     logger=logging.error)
                return JsonResponse(dict(code=500, msg='下载失败'))

            finally:
                driver.close()

        else:
            return JsonResponse(dict(code=400, msg='错误的请求'))


@ratelimit(key='ip', rate='1/m', block=settings.RATELIMIT_BLOCK)
@auth
@api_view(['GET'])
def oss_download(request):
    """
    从OSS上下载资源
    """

    if request.method == 'GET':
        email = request.session.get('email')
        if cache.get(email):
            return JsonResponse(dict(code=403, msg='下载请求过快'), status=403)

        try:
            user = User.objects.get(email=email, is_active=True)
            if not user.phone:
                return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))

            cache.set(email, True, timeout=settings.DOWNLOAD_INTERVAL)
            point = settings.OSS_RESOURCE_POINT
            if user.point < point:
                return JsonResponse(dict(code=400, msg='积分不足，请进行捐赠'))
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        key = request.GET.get('key', None)
        if not key:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        try:
            oss_resource = Resource.objects.get(key=key)
            if not aliyun_oss_check_file(oss_resource.key):
                logging.error(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
                ding(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
                oss_resource.is_audited = 0
                oss_resource.save()
                return JsonResponse(dict(code=400, msg='该资源暂时无法下载'))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=400, msg='资源不存在'))

        # 判断用户是否下载过该资源
        # 若没有，则给上传资源的用户赠送积分
        # 上传者下载自己的资源不会获得积分
        if user != oss_resource.user:
            if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
                oss_resource.user.point += 1
                oss_resource.user.save()

        DownloadRecord.objects.create(user=user,
                                      resource=oss_resource,
                                      download_device=user.login_device,
                                      download_ip=user.login_ip,
                                      used_point=settings.OSS_RESOURCE_POINT)

        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()

        url = aliyun_oss_sign_url(oss_resource.key)
        oss_resource.download_count += 1
        oss_resource.save()
        return JsonResponse(dict(code=200, url=url))


@auth
@api_view(['POST'])
def parse_resource(request):
    """
    爬取资源信息

    返回资源信息以及相关资源信息

    :param request:
    :return:
    """

    if request.method == 'POST':
        resource_url = request.data.get('url', None)
        if not resource_url:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        if not re.match(r'^(http(s)?://kns\.cnki\.net/KCMS/detail/).+$', resource_url):
            # 去除资源地址参数
            resource_url = resource_url.split('?')[0]

        # CSDN资源
        if re.match(r'^(http(s)?://download\.csdn\.net/download/).+$', resource_url):
            headers = {
                'authority': 'download.csdn.net',
                'referer': 'https://download.csdn.net/',
                'user-agent': get_random_ua()
            }
            with requests.get(resource_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    soup = BeautifulSoup(r.text, 'lxml')

                    # 版权受限，无法下载
                    # https://download.csdn.net/download/c_baby123/10791185
                    can_download = len(soup.select('div.resource_box a.copty-btn')) == 0
                    if can_download:
                        point = settings.CSDN_POINT
                    else:
                        point = None
                    resource = {
                        'title': soup.find('span', class_='resource_title').string,
                        'desc': soup.select('div.resource_description p')[0].text,
                        'tags': [tag.text for tag in soup.select('label.resource_tags a')],
                        'file_type': soup.select('dl.resource_box_dl dt img')[0]['src'].split('/')[-1].split('.')[0],
                        'point': point
                    }
                    return JsonResponse(dict(code=200, resource=resource))

                return JsonResponse(dict(code=500, msg='资源获取失败'))

        # 百度文库文档
        elif re.match(r'^(http(s)?://wenku\.baidu\.com/view/).+$', resource_url):
            """
            资源信息获取地址: https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id=
            """
            # https://wenku.baidu.com/view/c3853acaab00b52acfc789eb172ded630b1c9809.htm
            doc_id = resource_url.split('?')[0].split('://wenku.baidu.com/view/')[1].split('.')[0]
            logging.info(f'百度文库文档ID: {doc_id}')

            get_doc_info_url = f'https://wenku.baidu.com/api/doc/getdocinfo?callback=cb&doc_id={doc_id}'
            get_vip_free_doc_url = f'https://wenku.baidu.com/user/interface/getvipfreedoc?doc_id={doc_id}'
            headers = {
                'user-agent': get_random_ua()
            }
            with requests.get(get_doc_info_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    try:
                        data = json.loads(r.content.decode()[7:-1])
                        doc_info = data['docInfo']
                        # 判断是否是VIP专享文档
                        if doc_info.get('professionalDoc', None) == 1:
                            point = settings.WENKU_SPECIAL_DOC_POINT
                        elif doc_info.get('isPaymentDoc', None) == 0:
                            with requests.get(get_vip_free_doc_url, headers=headers) as _:
                                if _.status_code == requests.codes.OK and _.json()['status']['code'] == 0:
                                    if _.json()['data']['is_vip_free_doc']:
                                        point = settings.WENKU_VIP_FREE_DOC_POINT
                                    else:
                                        point = settings.WENKU_SHARE_DOC_POINT
                                else:
                                    return JsonResponse(dict(code=500, msg='资源获取失败'))
                        else:
                            point = None

                        file_type = doc_info['docType']
                        if file_type == '6':
                            file_type = 'PPTX'
                        elif file_type == '3':
                            file_type = 'PPT'
                        elif file_type == '1':
                            file_type = 'DOC'
                        elif file_type == '4':
                            file_type = 'DOCX'
                        elif file_type == '8':
                            file_type = 'TXT'
                        elif file_type == '7':
                            file_type = 'PDF'
                        elif file_type == '5':
                            file_type = 'XLSX'
                        elif file_type == '2':
                            file_type = 'XLS'
                        elif file_type == '12':
                            file_type = 'VSD'
                        elif file_type == '15':
                            file_type = 'PPS'
                        elif file_type == '13':
                            file_type = 'RTF'
                        elif file_type == '9':
                            file_type = 'WPS'
                        elif file_type == '19':
                            file_type = 'DWG'
                        else:
                            logging.error(f'未知文件格式: {file_type}, 资源地址: {resource_url}')
                            ding(f'未知文件格式: {file_type}, 资源地址: {resource_url}, docInfo: {json.dumps(doc_info)}')
                            file_type = 'UNKNOWN'

                        resource = {
                            'title': doc_info['docTitle'],
                            'tags': doc_info.get('newTagArray', []),
                            'desc': doc_info['docDesc'],
                            'file_type': file_type,
                            'point': point
                        }
                        return JsonResponse(dict(code=200, resource=resource))
                    except Exception as e:
                        ding(f'资源信息解析失败: {str(e)}，资源地址: {resource_url}, 用户: {request.session.get("email")}')
                        logging.error(f'资源信息解析失败: {str(e)}，资源地址: {resource_url}, 用户: {request.session.get("email")}')
                        return JsonResponse(dict(code=500, msg='资源获取失败'))
                else:
                    return JsonResponse(dict(code=500, msg='资源获取失败'))

        # 稻壳模板
        elif re.match(r'^(http(s)?://www\.docer\.com/(webmall/)?preview/).+$', resource_url):
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'host': 'www.docer.com',
                'referer': 'https://www.docer.com/',
                'user-agent': get_random_ua()
            }
            with requests.get(resource_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    soup = BeautifulSoup(r.text, 'lxml')
                    tags = [tag.text for tag in soup.select('li.preview__labels-item.g-link a')]
                    if '展开更多' in tags:
                        tags = tags[:-1]

                    # 获取所有的预览图片
                    preview_images = DocerPreviewImage.objects.filter(resource_url=resource_url).all()
                    if len(preview_images) > 0:
                        preview_images = [
                            {
                                'url': preview_image.url,
                                'alt': preview_image.alt,

                            } for preview_image in preview_images
                        ]
                    else:
                        driver = get_driver()
                        try:
                            driver.get(resource_url)
                            all_images = WebDriverWait(driver, 5).until(
                                EC.presence_of_all_elements_located(
                                    (By.XPATH, '//ul[@class="preview__img-list"]//img')
                                )
                            )
                            preview_images = []
                            preview_image_models = []
                            for image in all_images:
                                image_url = image.get_attribute('data-src')
                                image_alt = image.get_attribute('alt')
                                preview_images.append({
                                    'url': image_url,
                                    'alt': image_alt
                                })
                                preview_image_models.append(DocerPreviewImage(resource_url=resource_url,
                                                                              url=image_url,
                                                                              alt=image_alt))
                            DocerPreviewImage.objects.bulk_create(preview_image_models)
                        finally:
                            driver.close()

                    resource = {
                        'title': soup.find('h1', class_='preview__title').string,
                        'tags': tags,
                        'file_type': soup.select('span.m-crumbs-path a')[0].text,
                        'desc': soup.find('meta', attrs={'name': 'Description'})['content'],
                        'point': settings.DOCER_POINT,
                        'preview_images': preview_images
                    }
                    return JsonResponse(dict(code=200, resource=resource))

                return JsonResponse(dict(code=500, msg='资源获取失败'))

        # 知网下载
        # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
        # https://kns.cnki.net/KCMS/detail/ 官网
        elif re.match(r'^(http(s)?://kns\.cnki\.net/KCMS/detail/).+$', resource_url):
            headers = {
                'host': 'kns.cnki.net',
                'referer': resource_url,
                'user-agent': get_random_ua()
            }
            with requests.get(resource_url, headers=headers) as r:
                soup = BeautifulSoup(r.text, 'lxml')
                # 获取标签
                tags_exist = soup.find('label', attrs={'id': 'catalog_KEYWORD'})
                tags = []
                if tags_exist:
                    for tag in tags_exist.find_next_siblings('a'):
                        tags.append(tag.string.strip()[:-1])

                title = soup.select('div.wxTitle h2')[0].text
                desc = soup.find('span', attrs={'id': 'ChDivSummary'}).string
                has_caj = True if soup.find('a', attrs={'id': 'cajDown'}) else False
                has_pdf = True if soup.find('a', attrs={'id': 'pdfDown'}) else False
                resource = {
                    'title': title,
                    'desc': desc,
                    'tags': tags,
                    'caj_download': has_caj,  # 是否支持caj下载
                    'pdf_download': has_pdf,  # 是否支持pdf下载
                    'point': settings.ZHIWANG_POINT
                }
                return JsonResponse(dict(code=200, resource=resource))
        else:
            return JsonResponse(dict(code=400, msg='资源地址有误'))
