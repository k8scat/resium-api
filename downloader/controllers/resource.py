from threading import Thread
from time import sleep

from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.decorators import api_view
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
)
from downloader.services.resource.csdn import CsdnResource
from downloader.services.resource.docer import DocerResource
from downloader.services.resource.mbzj import MbzjResource
from downloader.services.resource.qiantu import QiantuResource
from downloader.services.resource.wenku import WenkuResource
from downloader.services.resource.zhiwang import ZhiwangResource
from downloader.utils import *


@auth
@api_view(["POST"])
def upload(request):
    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg="未登录"))

    file = request.FILES.get("file", None)
    if not file:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    if file.size > (2 * 10) * 1024 * 1024:
        return JsonResponse(
            dict(code=requests.codes.bad_request, msg="上传资源大小不能超过20MiB")
        )

    file_md5 = get_file_md5(file.open("rb"))
    if Resource.objects.filter(file_md5=file_md5).count():
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源已存在"))

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
            t = Thread(target=aliyun_oss_upload, args=(filepath, key))
            t.start()

            ding(f"有新的资源上传 {key}", uid=user.uid)
            return JsonResponse(dict(code=requests.codes.ok, msg="资源上传成功"))
        except Exception as e:
            ding(f"资源上传失败", error=e)
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
    key = request.GET.get("key", "")

    start = per_page * (page - 1)
    end = start + per_page

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
def get_resource_count(request):
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
def list_resource_tags(request):
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
def download(request):
    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
        if cache.get(uid) and not settings.DEBUG:
            return JsonResponse(
                dict(code=requests.codes.forbidden, msg="请求频率过快，请稍后再试！")
            )
        if not user.is_admin and not user.can_download:
            return JsonResponse(dict(code=requests.codes.bad_request, msg="未授权"))

        if not user.is_admin:
            cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg="未登录"))

    resource_url = request.data.get("url", None)

    # 下载返回类型（不包括直接在OSS找到的资源），file/url/email，默认file
    download_type = request.data.get("t", "file")
    if download_type == "email" and not user.email:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="账号未设置邮箱"))

    if not resource_url:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源地址不能为空"))

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split("?")[0]

    if re.match(settings.PATTERN_MBZJ, resource_url):
        resource_url = re.sub(r"\.shtml.*", ".shtml", resource_url)

    doc_id = None
    if re.match(settings.PATTERN_WENKU, resource_url):
        resource_url, doc_id = get_wenku_doc_id(resource_url)

    # 检查OSS是否存有该资源
    oss_resource = check_oss(resource_url)
    if oss_resource:
        if user.is_admin:
            point = 0
        else:
            point = request.data.get("point", None)
            if (
                point is None
                or (
                    re.match(settings.PATTERN_CSDN, resource_url)
                    and point != settings.CSDN_POINT
                )
                or (
                    re.match(settings.PATTERN_WENKU, resource_url)
                    and point
                    not in [
                        settings.WENKU_SHARE_DOC_POINT,
                        settings.WENKU_SPECIAL_DOC_POINT,
                        settings.WENKU_VIP_FREE_DOC_POINT,
                    ]
                )
                or (
                    re.match(settings.PATTERN_DOCER, resource_url)
                    and point != settings.DOCER_POINT
                )
                or (
                    re.match(settings.PATTERN_ZHIWANG, resource_url)
                    and point != settings.ZHIWANG_POINT
                )
                or (
                    re.match(settings.PATTERN_QIANTU, resource_url)
                    and point != settings.QIANTU_POINT
                )
                or (
                    re.match(settings.PATTERN_ITEYE, resource_url)
                    and point != settings.ITEYE_POINT
                )
                or (
                    re.match(settings.PATTERN_MBZJ, resource_url)
                    and point != settings.MBZJ_POINT
                )
            ):
                cache.delete(user.uid)
                return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

            if user.point < point:
                cache.delete(user.uid)
                return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

        # 新增下载记录
        DownloadRecord(user=user, resource=oss_resource, used_point=point).save()

        # 更新用户积分
        user.point -= point
        user.used_point += point
        user.save()
        PointRecord(
            user=user,
            used_point=point,
            comment="下载资源",
            url=resource_url,
            point=user.point,
        ).save()

        # 生成临时下载地址，10分钟有效
        url = aliyun_oss_sign_url(oss_resource.key)

        # 更新资源的下载次数
        oss_resource.download_count += 1
        oss_resource.save()

        if download_type == "email":
            subject = "[源自下载] 资源下载成功"
            html_message = render_to_string(
                "downloader/download_url.html", {"url": url}
            )
            plain_message = strip_tags(html_message)
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                return JsonResponse(
                    dict(
                        code=requests.codes.ok,
                        msg="下载成功，请前往邮箱查收！（如果未收到邮件，请检查是否被收入垃圾箱！）",
                        url=url,
                    )
                )
            except Exception as e:
                ding(
                    "资源下载地址邮件发送失败",
                    error=e,
                    uid=user.uid,
                    logger=logging.error,
                    need_email=True,
                )
                return JsonResponse(
                    dict(code=requests.codes.server_error, msg="邮件发送失败")
                )

        return JsonResponse(dict(code=requests.codes.ok, url=url))

    # CSDN资源下载
    if re.match(settings.PATTERN_CSDN, resource_url):
        if cache.get(settings.CSDN_DOWNLOADING_KEY):
            return JsonResponse(
                dict(code=requests.codes.forbidden, msg="当前下载人数过多，请稍后再尝试下载！")
            )
        cache.set(
            settings.CSDN_DOWNLOADING_KEY, True, settings.CSDN_DOWNLOADING_MAX_TIME
        )

        res = CsdnResource(resource_url, user)

    elif re.match(settings.PATTERN_ITEYE, resource_url):
        resource_url = "https://download.csdn.net/download/" + resource_url.split(
            "resource/"
        )[1].replace("-", "/")
        res = CsdnResource(resource_url, user)

    # 百度文库文档下载
    elif re.match(settings.PATTERN_WENKU, resource_url):
        if not doc_id:
            ding("[百度文库] 资源地址正则通过，但没有doc_id", resource_url=resource_url)
            return JsonResponse(dict(code=requests.codes.bad_request, msg="资源地址有误"))
        else:
            res = WenkuResource(resource_url, user, doc_id)

    # 稻壳模板下载
    elif re.match(settings.PATTERN_DOCER, resource_url):
        if resource_url.count("webmall") > 0:
            resource_url = resource_url.replace("/webmall", "")
        res = DocerResource(resource_url, user)

    elif re.match(settings.PATTERN_QIANTU, resource_url):
        res = QiantuResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        res = ZhiwangResource(resource_url, user)

    elif re.match(settings.PATTERN_MBZJ, resource_url):
        res = MbzjResource(resource_url, user)

    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    res.download()
    if res.err:
        if isinstance(res.err, dict):
            return JsonResponse(res.err)
        else:
            return JsonResponse(dict(code=requests.codes.server_error, msg=res.err))
    return JsonResponse(dict(code=requests.codes.ok, url=res.download_url))


@auth
@api_view()
def oss_download(request):
    """
    从OSS上下载资源
    """

    uid = request.session.get("uid")
    if cache.get(uid):
        return JsonResponse(dict(code=requests.codes.forbidden, msg="请求频率过快，请稍后再试！"))

    user = User.objects.get(uid=uid)
    cache.set(uid, True, timeout=settings.DOWNLOAD_INTERVAL)

    t = request.GET.get("t", "url")

    resource_id = request.GET.get("id", None)
    if resource_id and resource_id.isnumeric():
        resource_id = int(resource_id)
    else:
        cache.delete(user.uid)
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        oss_resource = Resource.objects.get(id=resource_id)
        if not aliyun_oss_check_file(oss_resource.key):
            logging.error(f"OSS资源不存在，请及时检查资源 {oss_resource.key}")
            ding(
                f"OSS资源不存在，请及时检查资源 {oss_resource.key}",
                uid=user.uid,
                logger=logging.error,
                need_email=True,
            )
            oss_resource.is_audited = 0
            oss_resource.save()
            cache.delete(user.uid)
            return JsonResponse(dict(code=requests.codes.bad_request, msg="该资源暂时无法下载"))
    except Resource.DoesNotExist:
        cache.delete(user.uid)
        return JsonResponse(dict(code=requests.codes.not_found, msg="资源不存在"))

    point = settings.OSS_RESOURCE_POINT + oss_resource.download_count - 1
    if user.point < point:
        cache.delete(user.uid)
        return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

    user.point -= point
    user.used_point += point
    user.save()
    PointRecord(
        user=user,
        point=user.point,
        comment="下载资源",
        used_point=point,
        resource=oss_resource,
    ).save()
    DownloadRecord.objects.create(
        user=user, resource=oss_resource, used_point=settings.OSS_RESOURCE_POINT
    )

    url = aliyun_oss_sign_url(oss_resource.key)
    oss_resource.download_count += 1
    oss_resource.save()

    if t == "url":
        return JsonResponse(dict(code=requests.codes.ok, url=url))
    elif t == "email":
        if not user.email:
            return JsonResponse(dict(code=requests.codes.bad_request, msg="未设置邮箱"))

        subject = "[源自下载] 资源下载成功"
        html_message = render_to_string("downloader/download_url.html", {"url": url})
        plain_message = strip_tags(html_message)
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            return JsonResponse(
                dict(
                    code=requests.codes.ok,
                    url=url,
                    msg="下载成功，请前往邮箱查收！（如果未收到邮件，请检查是否被收入垃圾箱！）",
                )
            )
        except Exception as e:
            ding(
                "资源下载地址邮件发送失败",
                error=e,
                uid=user.uid,
                logger=logging.error,
                need_email=True,
            )
            return JsonResponse(dict(code=requests.codes.server_error, msg="邮件发送失败"))


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

    logging.info(resource_url)

    if not re.match(settings.PATTERN_ZHIWANG, resource_url):
        # 去除资源地址参数
        resource_url = resource_url.split("?")[0]

    doc_id = None
    if re.match(settings.PATTERN_WENKU, resource_url):
        resource_url, doc_id = get_wenku_doc_id(resource_url)

    uid = request.session.get("uid")
    user = User.objects.get(uid=uid)

    # CSDN资源
    if re.match(settings.PATTERN_CSDN, resource_url):
        resource = CsdnResource(resource_url, user)

    elif re.match(settings.PATTERN_ITEYE, resource_url):
        resource_url = "https://download.csdn.net/download/" + resource_url.split(
            "resource/"
        )[1].replace("-", "/")
        resource = CsdnResource(resource_url, user)

    # 百度文库文档
    elif re.match(settings.PATTERN_WENKU, resource_url):
        resource = WenkuResource(resource_url, user, doc_id)

    # 稻壳模板
    elif re.match(settings.PATTERN_DOCER, resource_url):
        resource = DocerResource(resource_url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    elif re.match(settings.PATTERN_ZHIWANG, resource_url):
        resource = ZhiwangResource(resource_url, user)

    elif re.match(settings.PATTERN_QIANTU, resource_url):
        resource = QiantuResource(resource_url, user)

    elif re.match(settings.PATTERN_MBZJ, resource_url):
        resource = MbzjResource(resource_url, user)

    else:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="资源地址有误"))

    status, result = resource.parse()
    return JsonResponse(dict(code=status, resource=result))


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

    uid = request.session.get("uid")
    try:
        user = User.objects.get(uid=uid)
        point = settings.DOC_CONVERT_POINT
        if user.point < point:
            return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))
    except User.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.unauthorized, msg="未登录"))

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

    driver = get_driver(unique_folder)
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
            ding(f"[文档转换] 转换成功，{download_url}", uid=user.uid)
            return JsonResponse(dict(code=requests.codes.ok, url=download_url))
        except TimeoutException:
            DocConvertRecord(user=user).save()
            ding(f"[文档转换] 转换失败，{command}，{filepath}", need_email=True)
            return JsonResponse(
                dict(code=requests.codes.server_error, msg="出了点小问题，请尝试重新转换")
            )

    finally:
        driver.close()


@api_view()
def get_download_interval(request):
    """
    获取下载间隔

    :param request:
    :return:
    """

    return JsonResponse(
        dict(code=requests.codes.ok, download_interval=settings.DOWNLOAD_INTERVAL)
    )


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
