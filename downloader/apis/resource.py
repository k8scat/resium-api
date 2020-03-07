# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/15

"""
import logging
import os
import random
import re
import string
import uuid
from threading import Thread
from urllib import parse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse, FileResponse
from ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.decorators import auth
from downloader.models import Resource, User, ResourceComment, DownloadRecord
from downloader.serializers import ResourceSerializers, ResourceCommentSerializers
from downloader.utils import aliyun_oss_upload, get_file_md5, ding, aliyun_oss_sign_url, \
    check_download, add_cookies, get_driver, check_csdn, check_oss, aliyun_oss_check_file, \
    save_resource, send_email


@auth
@api_view(['POST'])
def upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file', None)

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
                email = request.session.get('email')
                try:
                    user = User.objects.get(email=email, is_active=True)
                except User.DoesNotExist:
                    return JsonResponse(dict(code=400, msg='错误的请求'))
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
                         is_audited=False, key=key, user=user, file_md5=file_md5,
                         download_count=0).save()

                # 开线程上传资源到OSS
                t = Thread(target=aliyun_oss_upload, args=(filepath, key))
                t.start()

                # 发送邮件通知
                subject = '[CSDNBot] 资源上传成功'
                content = '您上传的资源将由管理员审核。如果审核通过，当其他用户下载该资源时，您将获得1积分奖励。'
                send_email(subject, content, user.email)

                ding(f'有新的资源上传 {key}')
                return JsonResponse(dict(code=200, msg='资源上传成功'))
            except Exception as e:
                logging.error(e)
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
                return JsonResponse(dict(code=200, resource=ResourceSerializers(resource).data))
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
        key = request.GET.get('key', '')
        if page < 1:
            page = 1

        # 单页资源数
        page_count = 8
        start = page_count * (page - 1)
        end = start + page_count
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


@auth
@api_view(['GET'])
def download(request):
    """
    直接从CSDN或百度文库下载资源

    需要认证
    """
    if request.method == 'GET':
        user = None
        try:
            email = request.session.get('email')
            try:
                user = User.objects.get(email=email, is_active=True)
                if user.is_downloading:
                    return JsonResponse(dict(code=400, msg='不能同时下载多个资源'))
                user.is_downloading = True
                user.save()
            except User.DoesNotExist:
                return JsonResponse(dict(code=401, msg='未认证'))

            resource_url = request.GET.get('url', None)
            if not resource_url:
                return JsonResponse(dict(code=400, msg='资源地址不能为空'))
            # 去除资源地址参数
            resource_url = resource_url.split('?')[0]

            # 检查OSS是否存有该资源
            oss_resource = check_oss(resource_url)
            if oss_resource:
                # 判断用户是否下载过该资源
                # 若没有，则给上传资源的用户赠送下载积分
                if user != oss_resource.user:
                    if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
                        oss_resource.user.point += 1
                        oss_resource.user.save()

                # 新增下载记录
                DownloadRecord(user=user,
                               resource=oss_resource,
                               download_device=user.login_device,
                               download_ip=user.login_ip).save()
                # 生成临时下载地址
                url = aliyun_oss_sign_url(oss_resource.key)

                # 更新资源的下载次数
                oss_resource.download_count += 1
                oss_resource.save()

                return JsonResponse(dict(code=200, url=url))

            # 生成资源存放的唯一子目录
            uuid_str = str(uuid.uuid1())
            save_dir = os.path.join(settings.DOWNLOAD_DIR, uuid_str)
            while True:
                if os.path.exists(save_dir):
                    uuid_str = str(uuid.uuid1())
                    save_dir = os.path.join(settings.DOWNLOAD_DIR, uuid_str)
                else:
                    os.mkdir(save_dir)
                    break

            # CSDN资源下载
            if re.match(r'^(http(s)?://download\.csdn\.net/download/).+$', resource_url):
                logging.info(f'CSDN 资源下载: {resource_url}')

                # 账号冻结
                # return JsonResponse(dict(code=400, msg='本站今日CSDN资源下载已达上限'))

                if not check_csdn():
                    return JsonResponse(dict(code=400, msg='本站今日CSDN资源下载已达上限'))

                # 无下载记录且可用下载积分不足
                if user.point < 10:
                    return JsonResponse(dict(code=400, msg='下载积分不足，请进行捐赠'))

                driver = get_driver(uuid_str)
                csdn_account = None
                try:
                    # 先请求，再添加cookies
                    # selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
                    driver.get('https://download.csdn.net')
                    # 添加cookies，并返回使用的会员账号
                    csdn_account = add_cookies(driver, 'csdn')
                    # 访问资源地址
                    driver.get(resource_url)

                    soup = BeautifulSoup(driver.page_source, 'lxml')
                    # 版权受限
                    # https://download.csdn.net/download/c_baby123/10791185
                    cannot_download = len(soup.select('div.resource_box a.copty-btn'))
                    if cannot_download:
                        return JsonResponse(dict(code=400, msg='版权受限，无法下载'))
                    # 获取资源标题
                    title = soup.select('div.resource_box_info span.resource_title')[0].string
                    desc = soup.select('div.resource_box_desc div.resource_description p')[0].contents[0].string
                    category = '-'.join([cat.string for cat in soup.select('div.csdn_dl_bread a')[1:3]])
                    tags = settings.TAG_SEP.join([tag.string for tag in soup.select('div.resource_box_b label.resource_tags a')])
                    # logging.info(tags)

                    try:
                        # 点击VIP下载按钮
                        el = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.LINK_TEXT, "VIP下载"))
                        )
                        el.click()

                        # 点击弹框中的VIP下载
                        el = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            "(.//*[normalize-space(text()) and normalize-space(.)='为了良好体验，不建议使用迅雷下载'])[1]/following::a[1]"))
                        )
                        el.click()
                    except TimeoutException as e:
                        logging.error(e)
                        ding(f'CSDN资源下载失败: {str(e)}, 资源地址: {resource_url}, 下载用户: {user.email}')
                        return JsonResponse(dict(code=500, msg='下载失败'))

                    # 点击了VIP下载后一定要更新用户下载积分和会员账号使用下载积分，不管后面是否成功
                    # 更新用户的下载积分和已用下载积分
                    user.point -= 10
                    user.used_point += 10
                    user.save()

                    # 更新账号使用下载数
                    csdn_account.used_count += 1
                    csdn_account.save()

                    try:
                        filepath, filename = check_download(save_dir)
                    except TypeError:
                        return JsonResponse(dict(code=500, msg='下载失败'))
                    # 保存资源
                    t = Thread(target=save_resource, args=(resource_url, filename, filepath, title, tags, category, desc, user, csdn_account))
                    t.start()

                    f = open(filepath, 'rb')
                    response = FileResponse(f)
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                            safe=string.printable) + '"'

                    return response

                except Exception as e:
                    logging.error(e)
                    ding(f'下载出现未知错误：{str(e)}，用户：{user.email}，会员账号：{csdn_account.email if csdn_account else "无"}，资源地址：{resource_url}')
                    return JsonResponse(dict(code=500, msg='下载失败'))

                finally:
                    driver.quit()

            # 百度文库文档下载
            elif re.match(r'^(http(s)?://wenku\.baidu\.com/view/).+$', resource_url):
                logging.info(f'百度文库资源下载: {resource_url}')

                driver = get_driver(uuid_str)
                baidu_account = None
                try:
                    driver.get('https://www.baidu.com/')
                    # 添加cookies
                    baidu_account = add_cookies(driver, 'baidu')

                    driver.get(resource_url)

                    soup = BeautifulSoup(driver.page_source, 'lxml')
                    desc = soup.select('span.doc-desc-all')
                    title = soup.select('span.doc-header-title')[0].text
                    tags = settings.TAG_SEP.join([tag.text for tag in soup.select('div.tag-tips a')])
                    desc = desc[0].text.strip() if desc else ''
                    doc_type = soup.find('div', attrs={'style': 'display: block;', 'class': 'doc-tag'}).find('span').string
                    cats = '-'.join([item.text for item in soup.select('div.crumbs.ui-crumbs.mb10 li a')[1:]])

                    if doc_type not in ['VIP免费文档', '共享文档', 'VIP专享文档']:
                        return JsonResponse(dict(code=400, msg='此类资源无法下载: ' + doc_type))

                    if doc_type != 'VIP免费文档':
                        if user.point < 10:
                            return JsonResponse(dict(code=400, msg='下载积分不足，请进行捐赠'))
                        # 更新用户下载积分
                        user.point -= 10
                        user.used_point += 10
                        user.save()

                        # 更新账号使用下载数
                        baidu_account.used_count += 1
                        baidu_account.save()

                    # 显示下载对话框的按钮
                    show_download_modal_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.reader-download.btn-download'))
                    )
                    show_download_modal_button.click()

                    # 下载按钮
                    try:
                        # 首次下载
                        download_button = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, 'div.dialog-inner.tac > a.ui-bz-btn-senior.btn-diaolog-downdoc'))
                        )
                        # 取消转存网盘
                        cancel_wp_upload_check = WebDriverWait(driver, 5).until(
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
                            ding(f'百度文库下载失败: {doc_type}, 资源地址: {resource_url}, 下载用户: {user.email}')
                            return JsonResponse(dict(code=500, msg='下载失败'))

                    filepath, filename = check_download(save_dir)
                    # 保存资源
                    t = Thread(target=save_resource, args=(resource_url, filename, filepath, title, tags, cats, desc, user, baidu_account))
                    t.start()

                    f = open(filepath, 'rb')
                    response = FileResponse(f)
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                            safe=string.printable) + '"'

                    return response

                except Exception as e:
                    logging.error(e)
                    ding(f'下载出现未知错误：{str(e)}，用户：{user.email}，会员账号：{baidu_account.email if baidu_account else "无"}，资源地址：{resource_url}')
                    return JsonResponse(dict(code=500, msg='下载失败'))

                finally:
                    driver.quit()

            # 稻壳模板下载
            elif re.match(r'^(http(s)?://www\.docer\.com/(webmall/)?preview/).+$', resource_url):
                logging.info(f'稻壳模板下载: {resource_url}')

                if user.student:
                    if user.point < 1:
                        return JsonResponse(dict(code=400, msg='下载积分不足，请进行捐赠'))
                else:
                    if user.point < 5:
                        return JsonResponse(dict(code=400, msg='下载积分不足，请进行捐赠'))

                driver = get_driver(uuid_str)
                docer_account = None
                try:
                    driver.get('https://www.docer.com/')

                    # 添加cookies
                    docer_account = add_cookies(driver, 'docer')

                    driver.get(resource_url)

                    soup = BeautifulSoup(driver.page_source, 'lxml')
                    title = soup.find('h1', class_='preview__title').string
                    tags = [tag.text for tag in soup.select('li.preview__labels-item.g-link a')]
                    if '展开更多' in tags:
                        tags = tags[:-1]
                    tags = settings.TAG_SEP.join(tags)
                    category = soup.select('span.m-crumbs-path a')[0].text

                    # 获取下载按钮
                    download_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//span[@class='preview__btn preview__primary-btn--large preview__primary-btn']"))
                    )
                    download_button.click()

                    # 更新用户下载积分
                    if user.student:
                        user.point -= 1
                        user.used_point += 1
                    else:
                        user.point -= 5
                        user.used_point += 5
                    user.save()

                    # 更新账号使用下载数
                    docer_account.used_count += 1
                    docer_account.save()

                    filepath, filename = check_download(save_dir)

                    # 保存资源
                    t = Thread(target=save_resource, args=(resource_url, filename, filepath, title, tags, category, '', user, docer_account))
                    t.start()

                    f = open(filepath, 'rb')
                    response = FileResponse(f)
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                            safe=string.printable) + '"'

                    return response

                except Exception as e:
                    logging.error(e)
                    ding(
                        f'下载出现未知错误：{str(e)}，用户：{user.email}，会员账号：{docer_account.email if docer_account else "无"}，资源地址：{resource_url}')
                    return JsonResponse(dict(code=500, msg='下载失败'))

                finally:
                    driver.quit()

            else:
                return JsonResponse(dict(code=400, msg='错误的请求'))
        finally:
            if user and user.is_downloading:
                user.is_downloading = False
                user.save()


@ratelimit(key='ip', rate='1/10m', block=settings.RATELIMIT_BLOCK)
@auth
@api_view(['GET'])
def oss_download(request):
    """
    从OSS上下载资源

    需要认证
    """

    if request.method == 'GET':
        key = request.GET.get('key', '')
        if key == '':
            return JsonResponse(dict(code=400, msg='错误的请求'))

        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=401, msg='未认证'))

        try:
            oss_resource = Resource.objects.get(key=key)
            if not aliyun_oss_check_file(oss_resource.key):
                logging.error(f'OSS资源不存在，请及时检查资源 {oss_resource.key}')
                oss_resource.is_audited = 0
                oss_resource.save()
                return JsonResponse(dict(code=400, msg='该资源暂时无法下载'))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=400, msg='资源不存在'))

        # 判断用户是否下载过该资源
        # 若没有，则给上传资源的用户赠送下载积分
        if user != oss_resource.user:
            if not DownloadRecord.objects.filter(user=user, resource=oss_resource).count():
                oss_resource.user.point += 1
                oss_resource.user.save()

        DownloadRecord.objects.create(user=user,
                                      resource=oss_resource,
                                      download_device=user.login_device,
                                      download_ip=user.login_ip)

        url = aliyun_oss_sign_url(oss_resource.key)
        oss_resource.download_count += 1
        oss_resource.save()
        return JsonResponse(dict(code=200, url=url))


@auth
def parse_resource(request):
    """
    爬取资源信息

    返回资源信息以及相关资源信息

    :param request:
    :return:
    """

    if request.method == 'GET':
        resource_url = request.GET.get('url', None)
        if not resource_url:
            return JsonResponse(dict(code=400, msg='错误的请求'))

        resource_url = resource_url.split('?')[0]

        # CSDN资源
        if re.match(r'^(http(s)?://download\.csdn\.net/download/).+$', resource_url):
            headers = {
                'authority': 'download.csdn.net',
                'referer': 'https://download.csdn.net/',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'
            }
            with requests.get(resource_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    soup = BeautifulSoup(r.text, 'lxml')
                    resource = {
                        'title': soup.find('span', class_='resource_title').string,
                        'desc': soup.select('div.resource_description p')[0].text,
                        'tags': [tag.text for tag in soup.select('label.resource_tags a')],
                        'size': soup.select('strong.info_box span:nth-of-type(3) em')[0].text,
                        'file_type': soup.select('dl.resource_box_dl dt img')[0]['src'].split('/')[-1].split('.')[0]
                    }

                    return JsonResponse(dict(code=200, resource=resource))
                else:
                    return JsonResponse(dict(code=500, msg='资源获取失败'))

        # 百度文库文档
        elif re.match(r'^(http(s)?://wenku\.baidu\.com/view/).+$', resource_url):

            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'gzip, deflate, br',
                'host': 'wenku.baidu.com',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'
            }
            with requests.get(resource_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    soup = BeautifulSoup(r.content.decode('gbk'), 'lxml')
                    desc = soup.select('span.doc-desc-all')
                    logging.info(soup.find_all('div', attrs={'class': 'doc-tag'}))
                    resource = {
                        'title': soup.select('span.doc-header-title')[0].text,
                        'tags': [tag.text for tag in soup.select('div.tag-tips a')],
                        'desc': desc[0].text.strip() if desc else '',
                        'file_type': soup.select('h1.reader_ab_test.with-top-banner b')[0]['class'][1].split('-')[1],
                        # requests拿到的和selenium拿到的源代码是不一样的，requests的没有 style="display: block;"
                        # 'doc_type': soup.find('div', attrs={'class': 'doc-tag', 'style': 'display: block;'}).find('span').string
                    }
                    return JsonResponse(dict(code=200, resource=resource))
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
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'
            }
            with requests.get(resource_url, headers=headers) as r:
                if r.status_code == requests.codes.OK:
                    soup = BeautifulSoup(r.text, 'lxml')
                    tags = [tag.text for tag in soup.select('li.preview__labels-item.g-link a')]
                    if '展开更多' in tags:
                        tags = tags[:-1]
                    resource = {
                        'title': soup.find('h1', class_='preview__title').string,
                        'tags': tags,
                        'file_type': soup.select('span.m-crumbs-path a')[0].text
                    }
                    return JsonResponse(dict(code=200, resource=resource))
                else:
                    return JsonResponse(dict(code=500, msg='资源获取失败'))

        else:
            return JsonResponse(dict(code=400, msg='资源地址有误'))
