import json
import logging
import os
import random
import re
import uuid
from threading import Thread
from time import sleep

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from downloader.decorators import auth
from downloader.models import *
from downloader.serializers import (
    ResourceSerializers,
    ResourceCommentSerializers,
    UploadRecordSerializers,
    UserSerializers,
)
from downloader.services.resource.resource import (
    new_resource,
    download_from_oss,
    get_oss_resource,
)
from downloader.services.user import get_user_from_session
from downloader.utils import aliyun_oss, selenium
from downloader.utils.alert import alert
from downloader.utils.pagination import parse_pagination_args


@auth
@api_view(["POST"])
def upload(request):
    file = request.FILES.get("file", None)
    if not file:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))
    if file.size > (2 * 10) * 1024 * 1024:
        return JsonResponse(
            dict(code=requests.codes.bad_request, msg="上传资源大小不能超过20MiB")
        )

    file_md5 = file.md5(file.open("rb"))
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源已存在"))

    user = get_user_from_session(request)

    data = request.POST
    title = data.get("title", None)
    tags = data.get("tags", None)
    desc = data.get("desc", None)
    if title and tags and desc and file:
        try:
            filename = file.name
            key = f"{str(uuid.uuid1())}-{filename}"
            logging.info(f"Upload resource: {key}")
            filepath = os.path.join(settings.UPLOAD_DIR, key)
            # 写入文件，之后使用线程进行上传
            with open(filepath, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)
            resource = Resource.objects.create(
                title=title,
                desc=desc,
                tags=tags,
                filename=filename,
                size=file.size,
                download_count=0,
                is_audited=0,
                key=key,
                user=user,
                file_md5=file_md5,
                local_path=filepath,
            )

            UploadRecord(user=user, resource=resource).save()

            # 开线程上传资源到OSS
            t = Thread(target=aliyun_oss.upload, args=(filepath, key))
            t.start()

            alert(
                "用户上传资源",
                user=UserSerializers(user).data,
                resource=ResourceSerializers(resource).data,
            )
            return JsonResponse(dict(code=requests.codes.ok, msg="资源上传成功"))

        except Exception as e:
            alert("资源上传失败", user=UserSerializers(user).data, exception=e)
            return JsonResponse(dict(code=requests.codes.server_error, msg="资源上传失败"))

    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))


@auth
@api_view()
def check_file(request):
    """
    根据md5值判断资源是否存在

    :param request:
    :return:
    """

    file_md5 = request.GET.get("hash", None)
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源已存在"))
    return JsonResponse(dict(code=requests.codes.ok, msg="资源不存在"))


@auth
@api_view()
def list_uploaded_resources(request):
    """
    获取用户上传资源

    :param request:
    :return:
    """

    uid = request.session.get("uid")
    user = User.objects.get(uid=uid)
    upload_records = (
        UploadRecord.objects.filter(user=user).order_by("-create_time").all()
    )
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            resources=UploadRecordSerializers(upload_records, many=True).data,
        )
    )


@api_view()
def get_resource(request):
    resource_id = request.GET.get("id", None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
        try:
            resource = Resource.objects.get(id=resource_id, is_audited=1)
            preview_images = []
            if resource.url and re.match(settings.PATTERN_DOCER, resource.url):
                preview_images = [
                    {"url": preview_image.url, "alt": preview_image.alt}
                    for preview_image in DocerPreviewImage.objects.filter(
                        resource_url=resource.url
                    ).all()
                ]
            resource_ = ResourceSerializers(resource).data
            # todo: 可以尝试通过django-rest-framework实现，而不是手动去获取预览图的数据
            resource_.setdefault("preview_images", preview_images)
            resource_.setdefault(
                "point", settings.OSS_RESOURCE_POINT + resource.download_count - 1
            )
            return JsonResponse(dict(code=requests.codes.ok, resource=resource_))
        except Resource.DoesNotExist:
            return JsonResponse(dict(code=404, msg="资源不存在"))
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))


@api_view()
def list_resource_comments(request):
    resource_id = request.GET.get("id", None)
    if not resource_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        resource = Resource.objects.get(id=resource_id)
        comments = (
            ResourceComment.objects.filter(resource=resource)
            .order_by("-create_time")
            .all()
        )
        return JsonResponse(
            dict(
                code=requests.codes.ok,
                comments=ResourceCommentSerializers(comments, many=True).data,
            )
        )
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))


@auth
@api_view(["POST"])
def create_resource_comment(request):
    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    content = request.data.get("content", None)
    resource_id = request.data.get("id", None)
    if not content or not resource_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        resource = Resource.objects.get(id=resource_id, is_audited=1)
        resource_comment = ResourceComment.objects.create(
            user=user, resource=resource, content=content
        )
        return JsonResponse(
            dict(
                code=requests.codes.ok,
                msg="评论成功",
                comment=ResourceCommentSerializers(resource_comment).data,
            )
        )
    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))


@api_view()
def list_resources(request):
    """
    分页获取资源
    """
    page, per_page = parse_pagination_args(request)
    start = per_page * (page - 1)
    end = start + per_page

    key = request.GET.get("key", "")

    query = (Q(is_audited=1),)
    if key:
        query += (
            Q(title__icontains=key) | Q(desc__icontains=key) | Q(tags__icontains=key),
        )
    else:
        query += (~Q(url__startswith="https://www.docer.com"),)

    # Django模型-不区分大小写的查询/过滤 https://cloud.tencent.com/developer/ask/81558
    resources = (
        Resource.objects.filter(*query).order_by("-create_time").all()[start:end]
    )
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            resources=ResourceSerializers(resources, many=True).data,
        )
    )


@api_view()
def get_resource_count(request: Request):
    """
    获取资源的数量
    """
    key = request.GET.get("key", "")
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            count=Resource.objects.filter(
                Q(is_audited=1),
                Q(title__icontains=key)
                | Q(desc__icontains=key)
                | Q(tags__icontains=key),
            ).count(),
        )
    )


@api_view()
def list_resource_tags(request: Request):
    """
    获取所有的资源标签
    """
    tags = Resource.objects.values_list("tags")
    ret_tags = []
    for tag in tags:
        for t in tag[0].split(settings.TAG_SEP):
            if t not in ret_tags and t != "":
                ret_tags.append(t)

    return JsonResponse(
        dict(
            code=requests.codes.ok,
            tags=settings.TAG_SEP.join(
                random.sample(ret_tags, settings.SAMPLE_TAG_COUNT)
            ),
        )
    )


@auth
@api_view(["POST"])
def download(request: Request):
    user = get_user_from_session(request)
    if not user:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="用户不存在"))

    resource_url = request.data.get("url", None)
    if not resource_url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源地址不能为空"))

    key = f"download_limit:{user.uid}"
    if cache.get(key):
        return JsonResponse(dict(code=requests.codes.forbidden, msg="请求频率过快，请稍后再试！"))

    res = new_resource(resource_url, user)
    if not res:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="下载地址有误"))

    cache.set(key, True, timeout=settings.DOWNLOAD_INTERVAL)
    try:
        # 检查OSS是否存有该资源
        oss_resource = get_oss_resource(resource_url)
        if oss_resource:
            point = res.resource["point"]
            if user.point < point:
                return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

            download_url = download_from_oss(oss_resource, user, point)
            return JsonResponse(dict(code=requests.codes.ok, url=download_url))

        res.download()
        if res.err:
            if isinstance(res.err, dict):
                return JsonResponse(res.err)
            else:
                return JsonResponse(dict(code=requests.codes.server_error, msg=res.err))
        return JsonResponse(dict(code=requests.codes.ok, url=res.download_url))

    finally:
        cache.delete(key)


@auth
@api_view()
def oss_download(request: Request):
    resource_id = request.GET.get("id", None)
    if not resource_id or not resource_id.isnumeric():
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    resource_id = int(resource_id)
    user = get_user_from_session(request)
    try:
        oss_resource = Resource.objects.get(id=resource_id)
        if not aliyun_oss.check_file(oss_resource.key):
            logging.error(f"oss resource not exists: {oss_resource.key}")
            oss_resource.is_audited = 0
            oss_resource.save()
            return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))

    except Resource.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))

    point = settings.OSS_RESOURCE_POINT + oss_resource.download_count - 1
    if user.point < point:
        return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

    download_url = download_from_oss(oss_resource, user, point)
    return JsonResponse(dict(code=requests.codes.ok, url=download_url))


@auth
@api_view(["POST"])
def parse_resource(request):
    """
    爬取资源信息

    返回资源信息以及相关资源信息

    :param request:
    :return:
    """

    resource_url = request.data.get("url", None)
    if not resource_url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    uid = request.session.get("uid")
    user = User.objects.get(uid=uid)

    res = new_resource(resource_url, user)
    res.parse()
    return JsonResponse(dict(code=requests.codes.ok, resource=res.resource))


@auth
@api_view(["POST"])
def check_resource_existed(request):
    url = request.data.get("url", None)
    if not url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    is_resource_existed = Resource.objects.filter(url=url).count() > 0
    return JsonResponse(dict(code=requests.codes.ok, is_existed=is_resource_existed))


@auth
@api_view(["POST"])
def doc_convert(request):
    command = request.POST.get("c", None)
    file = request.FILES.get("file", None)
    if not command or not file:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    if command == "pdf2word":
        url = "https://converter.baidu.com/detail?type=1"
    elif command == "word2pdf":
        url = "https://converter.baidu.com/detail?type=12"
    elif command == "img2pdf":
        url = "https://converter.baidu.com/detail?type=16"
    elif command == "pdf2html":
        url = "https://converter.baidu.com/detail?type=3"
    elif command == "pdf2ppt":
        url = "https://converter.baidu.com/detail?type=8"
    elif command == "pdf2img":
        url = "https://converter.baidu.com/detail?type=11"
    elif command == "ppt2pdf":
        url = "https://converter.baidu.com/detail?type=14"
    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    user = get_user_from_session(request)
    point = settings.DOC_CONVERT_POINT
    if user.point < point:
        return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

    if file.size > 100 * 1000 * 1000:
        return JsonResponse(
            dict(code=requests.codes.bad_request, msg="上传资源大小不能超过100MB")
        )

    unique_folder = str(uuid.uuid1())
    save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
    while True:
        if os.path.exists(save_dir):
            unique_folder = str(uuid.uuid1())
            save_dir = os.path.join(settings.DOWNLOAD_DIR, unique_folder)
        else:
            os.mkdir(save_dir)
            break
    filepath = os.path.join(save_dir, file.name)
    with open(filepath, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)

    driver = selenium.get_driver(unique_folder)
    try:
        driver.get("https://converter.baidu.com/")
        baidu_account = BaiduAccount.objects.get(is_enabled=True)
        cookies = json.loads(baidu_account.cookies)
        for cookie in cookies:
            if "expiry" in cookie:
                del cookie["expiry"]
            driver.add_cookie(cookie)
        driver.get(url)
        sleep(3)
        upload_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, "upload_file"))
        )
        upload_input.send_keys(filepath)
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//p[@class='converterNameV']")
                )
            )
            download_url = (
                WebDriverWait(driver, 10)
                .until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//a[@class='dwon-document']")
                    )
                )
                .get_attribute("href")
            )
            # 保存文档转换记录
            DocConvertRecord(user=user, download_url=download_url, point=point).save()
            # 更新用户积分
            user.point -= point
            user.used_point += point
            user.save()
            PointRecord(
                user=user, used_point=point, point=user.point, comment="文档转换"
            ).save()
            return JsonResponse(dict(code=requests.codes.ok, url=download_url))

        except TimeoutException:
            DocConvertRecord(user=user).save()

            alert("百度文库文档转换失败", user=UserSerializers(user).data)
            return JsonResponse(dict(code=requests.codes.server_error, msg="转换失败"))

    finally:
        driver.close()


@api_view(["POST"])
def check_docer_existed(request):
    token = request.data.get("token", "")
    if token != settings.ADMIN_TOKEN:
        return JsonResponse(dict(code=requests.codes.forbidden))

    docer_url = request.data.get("url", "")
    if re.match(settings.PATTERN_DOCER, docer_url):
        if docer_url.count("/webmall") > 0:
            docer_url = docer_url.replace("/webmall", "")
        docer_existed = Resource.objects.filter(url=docer_url).count() > 0
        return JsonResponse(dict(code=requests.codes.ok, existed=docer_existed))

    else:
        return JsonResponse(dict(code=requests.codes.bad_request))
