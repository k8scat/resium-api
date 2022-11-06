import logging
import re

import requests
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request

from downloader.decorators import auth
from downloader.models import Article, ArticleComment
from downloader.serializers import (
    ArticleSerializers,
    ArticleCommentSerializers,
)
from downloader.services.article import parse_article
from downloader.services.point_record import add_point_record
from downloader.services.user import get_user_from_session, update_user_point
from downloader.utils.pagination import parse_pagination_args


@auth
@api_view(["POST"])
def parse_csdn_article(request: Request):
    user = get_user_from_session(request)
    point = settings.ARTICLE_POINT
    if user.point < point:
        return JsonResponse(dict(code=5000, msg="积分不足，请进行捐赠支持。"))

    url = request.data.get("url", None)
    if not re.match(r"^http(s)?://blog\.csdn\.net/.+/article/details/.+$", url):
        return JsonResponse(dict(code=requests.codes.bad_request, msg="无效的文章地址"))
    if url.find("?") != -1:
        url = url.split("?")[0]

    result = parse_article(url, user)
    if not result:
        return JsonResponse(dict(code=requests.codes.server_error))

    article = result
    update_user_point(user, point)
    add_point_record(user, point, url, comment="解析CSDN文章")
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            article=ArticleSerializers(article).data,
        )
    )


@api_view()
def list_articles(request: Request):
    page, per_page = parse_pagination_args(request)
    key = request.GET.get("key", "")

    start = per_page * (page - 1)
    end = start + per_page
    articles = (
        Article.objects.filter(
            Q(title__icontains=key)
            | Q(desc__icontains=key)
            | Q(content__icontains=key)
            | Q(tags__icontains=key)
        )
        .order_by("-create_time")
        .all()[start:end]
    )
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            articles=ArticleSerializers(articles, many=True).data,
        )
    )


@api_view()
def get_article_count(request):
    key = request.GET.get("key", "")
    return JsonResponse(
        dict(
            code=requests.codes.ok,
            count=Article.objects.filter(
                Q(title__icontains=key)
                | Q(desc__icontains=key)
                | Q(tags__icontains=key)
                | Q(content__icontains=key)
            ).count(),
        )
    )


@api_view()
def get_article(request: Request):
    article_id = request.GET.get("id", None)
    if not article_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        article = Article.objects.get(id=article_id)
        article.view_count += 1
        article.save()

        ignored_content = """<svg style="display: none;" xmlns="http://www.w3.org/2000/svg">
        <path d="M5,0 0,2.5 5,5z" id="raphael-marker-block" stroke-linecap="round" style="-webkit-tap-highlight-color: rgba(0, 0, 0, 0);"></path>
        </svg>"""
        article.content = article.content.replace(ignored_content, "")
        return JsonResponse(
            dict(code=requests.codes.ok, article=ArticleSerializers(article).data)
        )
    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="文章不存在"))


@auth
@api_view(["POST"])
def create_article_comment(request: Request):
    content = request.data.get("content")
    article_id = request.data.get("id")
    if not content or not article_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    user = get_user_from_session(request)
    try:
        article = Article.objects.get(id=article_id)
        article_comment = ArticleComment.objects.create(
            user=user, article=article, content=content
        )
        return JsonResponse(
            dict(
                code=requests.codes.ok,
                msg="评论成功",
                comment=ArticleCommentSerializers(article_comment).data,
            )
        )

    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="文章不存在"))

    except Exception as e:
        logging.error(e)
        return JsonResponse(dict(code=requests.codes.server_error))


@api_view()
def list_article_comments(request):
    article_id = request.GET.get("id", None)
    if not article_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg="错误的请求"))

    try:
        article = Article.objects.get(id=article_id)
        comments = (
            ArticleComment.objects.filter(article=article)
            .order_by("-create_time")
            .all()
        )
        return JsonResponse(
            dict(
                code=requests.codes.ok,
                comments=ArticleCommentSerializers(comments, many=True).data,
            )
        )

    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg="文章不存在"))

    except Exception as e:
        logging.error(e)
        return JsonResponse(dict(code=requests.codes.server_error))
