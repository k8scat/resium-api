import json
import logging
from typing import Tuple

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.conf import settings

from downloader.models import (
    Article,
    DownloadAccount,
    DOWNLOAD_ACCOUNT_TYPE_CSDN,
    DOWNLOAD_ACCOUNT_STATUS_ENABLED,
    User,
)
from downloader.utils import browser


def parse_article(url: str, user: User) -> Tuple[Article] | None:
    try:
        article = Article.objects.get(url=url)
        return article

    except Article.DoesNotExist:
        download_account = DownloadAccount.objects.filter(
            type=DOWNLOAD_ACCOUNT_TYPE_CSDN, status=DOWNLOAD_ACCOUNT_STATUS_ENABLED
        ).first()
        if not download_account:
            logging.warning("download_account not found")
            return None

        download_account_config = json.loads(download_account.config)
        headers = {
            "cookie": download_account_config.get("cookie", ""),
            "user-agent": browser.get_random_ua(),
        }
        with requests.get(url, headers=headers) as r:
            if r.status_code != requests.codes.ok:
                logging.error(
                    f"request {url} failed, code: {r.status_code}, text: {r.text}"
                )
                return None

            try:
                soup = BeautifulSoup(r.text, "lxml")
                # VIP文章
                is_vip = len(soup.select("span.vip_article")) > 0

                # 文章标题
                title = ""
                els = soup.select("h1.title-article")
                if len(els) > 0:
                    title = els[0].string

                # 文章作者
                author = ""
                els = soup.select("a.follow-nickName")
                if len(els) > 0:
                    author = els[0].string
                # 作者获取失败: https://blog.csdn.net/jiqiren_dasheng/article/details/103758891
                if not author:
                    author = "hsowan"

                # 文章内容
                content = ""
                el = soup.find("div", attrs={"id": "content_views"})
                if el and isinstance(el, Tag):
                    content = el.text
                css_links = [
                    str(link) for link in soup.select("div#article_content link")
                ]
                content = "".join(css_links) + content

                # 文章简介
                desc = ""
                el = soup.find("meta", attrs={"name": "description"})
                if isinstance(el, Tag):
                    desc = el.get("content", "")

                tags = [
                    tag.string.strip()
                    for tag in soup.select("a.tag-link")
                    if tag.get("data-report-click", None)
                ]

                article = Article.objects.create(
                    url=url,
                    title=title,
                    content=content,
                    author=author,
                    desc=desc,
                    is_vip=is_vip,
                    user=user,
                    tags=settings.TAG_SEP.join(tags),
                )
                return article

            except Exception as e:
                logging.error(f"failed to parse article: {e}")
                return None

    except Exception as e:
        logging.error(f"failed to parse article: {e}")
        return None
