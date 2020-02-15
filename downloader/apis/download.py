# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import string
from threading import Thread
from urllib import parse

from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from django.http import JsonResponse, HttpResponse, FileResponse

from downloader.decorators import auth
from downloader.serializers import *
from downloader.utils import *
from downloader import params


@auth
@swagger_auto_schema(method='get', manual_parameters=[params.resource_url])
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

            resource_url = request.GET.get('url', '')
            if resource_url == '':
                return JsonResponse(dict(code=400, msg='资源地址不能为空'))
            # 去除资源地址参数
            resource_url = resource_url.split('?')[0]

            dr = None
            has_downloaded = False  # 用于后面判断是否需要扣除用户可用下载数
            try:
                # 判断用户是否存在下载记录
                dr = DownloadRecord.objects.get(user=user, resource_url=resource_url, is_deleted=False)
                has_downloaded = True
            except DownloadRecord.DoesNotExist:
                pass

            # 检查OSS是否存有该资源
            oss_resource = check_oss(resource_url)
            if oss_resource:
                if not dr and user.valid_count <= 0:
                    return JsonResponse(dict(code=400, msg='可用下载数已用完'))

                file = aliyun_oss_get_file(oss_resource.key)
                response = FileResponse(file)
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="' + parse.quote(oss_resource.filename,
                                                                                        safe=string.printable) + '"'
                # 更新资源的下载次数
                oss_resource.download_count += 1
                oss_resource.save()

                # 更新下载时间
                dr.update_time = datetime.datetime.now()
                dr.save()
                return response
            else:
                logging.error('OSS没有找到资源')

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

            if resource_url.startswith('https://download.csdn.net/download/'):
                logging.info(f'CSDN 资源下载: {resource_url}')

                # 无下载记录且可用下载数不足
                if not dr and user.valid_count <= 0:
                    return JsonResponse(dict(code=400, msg='可用下载数已用完'))

                if not check_csdn():
                    return JsonResponse(dict(code=400, msg='本平台CSDN资源今日可下载数已用尽，请明日再来！'))

                r = requests.get(resource_url)
                title = None
                if r.status_code == 200:
                    try:
                        soup = BeautifulSoup(r.text, 'lxml')
                        # 版权受限
                        cannot_download = len(soup.select('div.resource_box a.copty-btn'))
                        if cannot_download:
                            return JsonResponse(dict(code=400, msg='版权受限，无法下载'))
                        title = soup.select('dl.resource_box_dl span.resource_title')[0].string
                    except Exception as e:
                        logging.error(e)
                        ding('资源名称获取失败 ' + str(e))
                        return JsonResponse(dict(code=500, msg='下载失败'))

                # 可能出现存在下载记录，但OSS上没有存储资源
                if isinstance(dr, DownloadRecord):
                    dr.update_time = datetime.datetime.now()
                    dr.save()
                else:
                    # 保存下载记录
                    dr = DownloadRecord.objects.create(user=user, resource_url=resource_url, title=title)

                driver = get_driver(uuid_str)
                try:
                    # 先请求，再添加cookies
                    # selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
                    driver.get('https://download.csdn.net')
                    # 添加cookies
                    account = add_cookie(driver, 'csdn')
                    # 保存所使用的会员账号信息
                    dr.account = account.email
                    dr.save()

                    # 访问资源地址
                    driver.get(resource_url)

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

                    filepath, filename = check_download(save_dir)
                    # 保存资源
                    t = Thread(target=save_csdn_resource, args=(resource_url, filename, filepath, title))
                    t.start()

                    f = open(filepath, 'rb')
                    response = FileResponse(f)
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                            safe=string.printable) + '"'

                    if not has_downloaded:
                        # 更新用户的可用下载数和已用下载数
                        user.valid_count -= 1
                        user.used_count += 1
                        user.save()
                        # 更新账号使用下载数
                        account.used_count += 1
                        account.save()

                    return response

                except Exception as e:
                    if dr:
                        dr.is_deleted = True
                        dr.save()
                    logging.error(e)
                    ding(f'下载出现未知错误（{resource_url}） ' + str(e))
                    return JsonResponse(dict(code=500, msg='下载失败'))

                finally:
                    driver.quit()

            elif resource_url.startswith('https://wenku.baidu.com/view/'):
                logging.info(f'百度文库资源下载: {resource_url}')

                dr = None
                driver = get_driver(uuid_str)
                try:
                    driver.get('https://www.baidu.com/')
                    # 添加cookies
                    account = add_cookie(driver, 'baidu')

                    driver.get(resource_url)

                    # VIP免费文档 共享文档 VIP专享文档 付费文档 VIP尊享8折文档
                    doc_tag = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                                                        "//div[contains(@class, 'bd doc-reader')]/div/div[contains(@style, 'display: block;')]/span"))
                    ).text
                    # ['VIP免费文档', '共享文档', 'VIP专享文档']
                    if doc_tag not in ['VIP免费文档', '共享文档', 'VIP专享文档']:
                        return JsonResponse(dict(code=400, msg='此类资源无法下载: ' + doc_tag))

                    if not has_downloaded and doc_tag != 'VIP免费文档':
                        if user.valid_count <= 0:
                            return JsonResponse(dict(code=400, msg='可用下载数已用完'))

                    # 文档标题
                    title = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//h1[contains(@class, 'reader_ab_test with-top-banner')]/span"))
                    ).text

                    # 可能出现存在下载记录，但OSS上没有存储资源
                    if isinstance(dr, DownloadRecord):
                        dr.update_time = datetime.datetime.now()
                        dr.save()
                    else:
                        # 保存下载记录
                        dr = DownloadRecord.objects.create(user=user, resource_url=resource_url, title=title,
                                                           account=account.email)

                    # 文档标签，可能不存在
                    # find_elements_by_xpath 返回的是一个List
                    tags = []
                    tag_els = driver.find_elements_by_xpath("//div[@class='tag-tips']/a")
                    for tag_el in tag_els:
                        tags.append(tag_el.text)
                    tags = settings.TAG_SEP.join(tags)

                    # 文档分类
                    cat_els = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//div[@id='page-curmbs']/ul//a"))
                    )[1:]
                    cats = []
                    for cat_el in cat_els:
                        cats.append(cat_el.text)
                    cats = '-'.join(cats)

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
                        if doc_tag != 'VIP专享文档':
                            # 已转存过此文档
                            download_button = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.ID, 'WkDialogOk'))
                            )
                            download_button.click()

                    filepath, filename = check_download(save_dir)
                    # 保存资源
                    t = Thread(target=save_wenku_resource, args=(resource_url, filename, filepath, title, tags, cats))
                    t.start()

                    f = open(filepath, 'rb')
                    response = FileResponse(f)
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="' + parse.quote(filename,
                                                                                            safe=string.printable) + '"'

                    if not has_downloaded and doc_tag != 'VIP免费文档':
                        user.valid_count -= 1
                        user.used_count += 1
                        user.save()
                        # 更新账号使用下载数
                        account.used_count += 1
                        account.save()

                    return response

                except Exception as e:
                    if dr:
                        dr.is_deleted = True
                        dr.save()
                    logging.error(e)
                    ding(f'下载出现未知错误（{resource_url}） ' + str(e))
                    return JsonResponse(dict(code=500, msg='下载失败'))

                finally:
                    driver.quit()

            else:
                return JsonResponse(dict(code=400, msg='错误的请求'))
        finally:
            if user and user.is_downloading:
                user.is_downloading = False
                user.save()


@auth
@swagger_auto_schema(method='get')
@api_view(['GET'])
def download_record(request):
    """
    获取用户所有的下载记录

    需要认证
    """

    if request.method == 'GET':
        email = request.session.get('email')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse(dict(code=404, msg='用户不存在'))

        download_records = DownloadRecord.objects.order_by('-update_time').filter(user=user, is_deleted=False).all()
        return JsonResponse(dict(code=200, msg='获取下载记录成功',
                                 download_records=DownloadRecordSerializers(download_records, many=True).data))


@auth
@swagger_auto_schema(method='get', manual_parameters=[params.page, params.key])
@api_view(['GET'])
def resource(request):
    """
    分页获取资源
    """
    if request.method == 'GET':
        page = int(request.GET.get('page', 1))
        key = request.GET.get('key', '')
        if page < 1:
            page = 1

        start = 5 * (page - 1)
        end = start + 5
        # https://cloud.tencent.com/developer/ask/81558
        resources = Resource.objects.order_by('-create_time').filter(Q(is_audited=1),
                                                                     Q(title__icontains=key) |
                                                                     Q(desc__icontains=key) |
                                                                     Q(tags__icontains=key)).all()[start:end]
        return JsonResponse(dict(code=200, resources=ResourceSerializers(resources, many=True).data))


@auth
@swagger_auto_schema(method='get', manual_parameters=[params.key])
@api_view(['GET'])
def resource_count(request):
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
@swagger_auto_schema(method='get')
@api_view(['GET'])
def resource_tags(request):
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
        return JsonResponse(dict(code=200, tags='#sep#'.join(ret_tags)))


@ratelimit(key='ip', rate='1/m', block=True)
@auth
@swagger_auto_schema(method='get', manual_parameters=[params.resource_key])
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
                oss_resource.delete()
                return JsonResponse(dict(code=400, msg='资源已被删除'))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=400, msg='资源不存在'))

        try:
            dr = DownloadRecord.objects.get(Q(resource_url=oss_resource.url) | Q(resource=oss_resource), user=user, is_deleted=False)
            dr.update_time = datetime.datetime.now()
            dr.save()
        except DownloadRecord.DoesNotExist:
            DownloadRecord.objects.create(user=user, resource_url=oss_resource.url, resource=oss_resource, title=oss_resource.title)

        file = aliyun_oss_get_file(oss_resource.key)
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="' + parse.quote(oss_resource.filename,
                                                                                safe=string.printable) + '"'
        oss_resource.download_count += 1
        oss_resource.save()
        return response


@swagger_auto_schema(method='get')
@api_view(['GET'])
def refresh_csdn_cookies(request):
    """
    更新CSDN cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', None)
        if token == settings.ADMIN_TOKEN:
            t = Thread(target=csdn_auto_login)
            t.start()
        return HttpResponse('')


@swagger_auto_schema(method='get')
@api_view(['GET'])
def refresh_baidu_cookies(request):
    """
    更新百度 cookies
    """
    if request.method == 'GET':
        token = request.GET.get('token', '')
        if token == settings.ADMIN_TOKEN:
            t = Thread(target=baidu_auto_login)
            t.start()
        return HttpResponse('')
