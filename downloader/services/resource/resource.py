import logging
import random
import re
import string

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from downloader.models import User, Resource, DownloadRecord, PointRecord
from downloader.serializers import UserSerializers, ResourceSerializers
from downloader.services.resource.base import BaseResource
from downloader.services.resource.csdn import CsdnResource
from downloader.services.resource.docer import DocerResource
from downloader.services.resource.wenku import WenkuResource
from downloader.utils import aliyun_oss, file, browser
from downloader.utils.alert import alert


def new_resource(url: str, user: User) -> BaseResource | None:
    # CSDN资源
    if re.match(settings.PATTERN_CSDN, url) or re.match(settings.PATTERN_ITEYE, url):
        return CsdnResource(url, user)

    # 百度文库文档
    if re.match(settings.PATTERN_WENKU, url):
        return WenkuResource(url, user)

    # 稻壳模板
    if re.match(settings.PATTERN_DOCER, url):
        return DocerResource(url, user)

    # 知网下载
    # http://kns-cnki-net.wvpn.ncu.edu.cn/KCMS/detail/ 校园
    # https://kns.cnki.net/KCMS/detail/ 官网
    # if re.match(settings.PATTERN_ZHIWANG, url):
    #     return ZhiwangResource(url, user)

    # if re.match(settings.PATTERN_QIANTU, url):
    #     return QiantuResource(url, user)

    # if re.match(settings.PATTERN_MBZJ, url):
    #     return MbzjResource(url, user)

    return None


def download_from_oss(resource: Resource, user: User, point: int) -> str:
    user.point -= point
    user.used_point += point
    user.save()

    DownloadRecord.objects.create(user=user, resource=resource, used_point=point)
    PointRecord.objects.create(
        user=user,
        used_point=point,
        comment="下载资源",
        url=resource.url,
        point=user.point,
    )

    # 生成临时下载地址，10分钟有效
    download_url = aliyun_oss.sign_url(resource.key)

    # 更新资源的下载次数
    resource.download_count += 1
    resource.save()

    try:
        subject = "[源自下载] 资源下载成功"
        html_message = render_to_string(
            "downloader/download_url.html", {"url": download_url}
        )
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        alert(
            "资源下载邮件发送失败",
            exception=e,
            user=UserSerializers(user).data,
            resource=ResourceSerializers(resource).data,
        )
    finally:
        return download_url


def get_oss_resource(url: str) -> Resource | None:
    try:
        resource = Resource.objects.get(url=url, is_audited=1)
        # 虽然数据库中有资源信息记录，但资源可能还未上传到oss
        # 如果oss上没有存储资源，则提醒管理员检查资源
        if not aliyun_oss.check_file(resource.key):
            resource.delete()
            alert("资源存在记录，但找不到OSS存储", key=resource.key, url=resource.url)
            return None

        return resource

    except Resource.DoesNotExist:
        return None


def upload_csdn_resource(resource: Resource, cookie: str):
    if not re.match(settings.PATTERN_CSDN, resource.url):
        headers = {
            "cookie": cookie,
            "user-agent": browser.get_random_ua(),
            "referer": "https://download.csdn.net/upload",
            "origin": "https://download.csdn.net",
        }
        # 将资源与其他文件进行压缩，获得到不同的MD5
        filepath = file.zip_file(resource.local_path)
        file_md5 = file.md5(open(filepath, "rb"))
        title = (
            resource.title
            + f"[{''.join(random.sample(string.digits + string.ascii_letters, 6))}]"
        )
        tags = resource.tags.replace(settings.TAG_SEP, ",").split(",")
        if len(tags) > 5:
            tags = ",".join(tags[:5])
        elif len(tags) == 1 and tags[0] == "":
            # 存在没有tag的情况
            # ''.split(',') => ['']
            tags = "好资源"
        else:
            tags = ",".join(tags)

        if len(resource.desc) < 50:
            desc = (
                '源自开发者，关注"源自开发者"公众号，每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享。 '
                + resource.desc
            )
        elif re.match(settings.PATTERN_DOCER, resource.url):
            desc = '源自开发者，关注"源自开发者"公众号，每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享。 '
        else:
            desc = (
                '源自开发者，关注"源自开发者"公众号，每天更新Python、Django、爬虫、Vue.js、Nuxt.js、ViewUI、Git、CI/CD、Docker、公众号开发、浏览器插件开发等技术分享。 '
                + resource.desc
            )

        payload = {
            "fileMd5": file_md5,
            "sourceid": "",
            "file_title": title,
            "file_type": 4,
            "file_primary": 15,  # 课程资源
            "file_category": 15012,  # 专业指导
            "resource_score": 5,
            "file_tag": tags,
            "file_desc": desc,
            "cb_agree": True,
        }
        files = [("user_file", open(filepath, "rb"))]
        with requests.post(
            "https://download.csdn.net/upload",
            headers=headers,
            data=payload,
            files=files,
        ) as r:
            if r.status_code != requests.codes.OK:
                logging.error(
                    f"failed to upload csdn resource, code: {r.status_code}, text: {r.text}"
                )
