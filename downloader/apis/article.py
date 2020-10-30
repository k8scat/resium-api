# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/20

"""
import logging
import re

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import CsdnAccount, Article, User, ArticleComment, PointRecord
from downloader.serializers import ArticleSerializers, ArticleCommentSerializers
from downloader.utils import ding, get_random_ua


@auth
@api_view(['POST'])
def parse_csdn_article(request):
    uid = request.session.get('uid')
    try:
        user = User.objects.get(uid=uid)
        point = settings.ARTICLE_POINT
        if user.point < point:
            return JsonResponse(dict(code=5000, msg='积分不足，请进行捐赠支持。'))
        if not user.can_download:
            return JsonResponse(dict(code=400, msg='错误的请求'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未认证'))

    article_url = request.data.get('url', None)
    if not article_url or not re.match(r'^http(s)?://blog\.csdn\.net/.+/article/details/.+$', article_url):
        return JsonResponse(dict(code=400, msg='错误的请求'))

    article_url = article_url.split('?')[0]
    try:
        article = Article.objects.get(id=7)
        return JsonResponse(dict(code=200, article=ArticleSerializers(article).data))

    except Article.DoesNotExist:
        csdn_account = CsdnAccount.objects.get(is_enabled=True)
        headers = {
            'cookie': csdn_account.cookies,
            'user-agent': get_random_ua()
        }
        with requests.get(article_url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                try:
                    soup = BeautifulSoup(r.text, 'lxml')
                    # VIP文章
                    is_vip = len(soup.select('span.vip_article')) > 0
                    # 文章标题
                    title = soup.select('h1.title-article')[0].string
                    # 文章作者
                    author = soup.select('a.follow-nickName')[0].string
                    # 作者获取失败: https://blog.csdn.net/jiqiren_dasheng/article/details/103758891
                    if author is None:
                        author = 'hsowan'
                    # 文章内容
                    content = str(soup.find('div', attrs={'id': 'content_views'}))
                    css_links = soup.select('div#article_content link')
                    for css_link in css_links:
                        content = str(css_link) + content
                    # 文章简介
                    desc = soup.find('meta', attrs={'name': 'description'})['content']
                    tags = settings.TAG_SEP.join(
                        [tag.string.strip() for tag in soup.select('a.tag-link') if tag.get('data-report-click', None)])
                    article = Article.objects.create(url=article_url, title=title, content=content,
                                                     author=author, desc=desc, is_vip=is_vip,
                                                     tags=tags, user=user)

                    user.point -= point
                    user.used_point += point
                    user.save()
                    PointRecord(user=user, used_point=point,
                                url=article_url, comment='解析CSDN文章',
                                point=user.point).save()
                    return JsonResponse(dict(code=requests.codes.ok, article=ArticleSerializers(article).data))

                except Exception as e:
                    ding(f'文章解析失败', error=e,
                         resource_url=article_url, logger=logging.error,
                         need_email=True)
                    return JsonResponse(dict(code=requests.codes.internal_server_error))

            ding(f'文章获取失败: {article_url}',
                 need_email=True,
                 uid=uid,
                 error=r.text)
            return JsonResponse(dict(code=requests.codes.server_error, msg='文章获取失败'))


@api_view()
def list_articles(request):
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        page = int(page)
        if page < 1:
            page = 1
        per_page = int(per_page)
        if per_page > 20:
            per_page = 20
    except ValueError:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    key = request.GET.get('key', '')

    start = per_page * (page - 1)
    end = start + per_page
    articles = Article.objects.filter(Q(title__icontains=key) |
                                      Q(desc__icontains=key) |
                                      Q(content__icontains=key) |
                                      Q(tags__icontains=key)).order_by('-create_time').all()[start:end]
    return JsonResponse(dict(code=requests.codes.ok, articles=ArticleSerializers(articles, many=True).data))


@api_view()
def list_recommend_articles(request):
    pass


@api_view()
def get_article_count(request):
    key = request.GET.get('key', '')
    return JsonResponse(dict(code=requests.codes.ok, count=Article.objects.filter(Q(title__icontains=key) |
                                                                                  Q(desc__icontains=key) |
                                                                                  Q(tags__icontains=key) |
                                                                                  Q(content__icontains=key)).count()))


@api_view()
def get_article(request):
    article_id = request.GET.get('id', None)
    if not article_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        article = Article.objects.get(id=article_id)
        article.view_count += 1
        article.save()
        return JsonResponse(dict(code=requests.codes.ok, article=ArticleSerializers(article).data))
    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='文章不存在'))


@auth
@api_view(['POST'])
def create_article_comment(request):
    uid = request.session.get('uid')
    user = User.objects.get(uid=uid)

    content = request.data.get('content')
    article_id = request.data.get('id')
    if not content or not article_id:
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    try:
        article = Article.objects.get(id=article_id)
        article_comment = ArticleComment.objects.create(user=user, article=article, content=content)
        return JsonResponse(dict(code=requests.codes.ok,
                                 msg='评论成功',
                                 comment=ArticleCommentSerializers(article_comment).data))
    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found, msg='文章不存在'))


@api_view()
def list_article_comments(request):
    article_id = request.GET.get('id', None)
    if not article_id:
        return JsonResponse(dict(code=requests.codes.bad_request,
                                 msg='错误的请求'))

    try:
        article = Article.objects.get(id=article_id)
        comments = ArticleComment.objects.filter(article=article).order_by('-create_time').all()
        return JsonResponse(dict(code=requests.codes.ok,
                                 comments=ArticleCommentSerializers(comments, many=True).data))
    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found,
                                 msg='文章不存在'))


@api_view(['POST'])
def check_article_existed(request):
    token = request.data.get('token', '')
    if token != settings.ADMIN_TOKEN:
        return JsonResponse(dict(code=requests.codes.forbidden))

    url = request.data.get('url', '')
    if not url or not re.match(r'^http(s)?://blog\.csdn\.net/.+/article/details/.+$', url):
        return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))

    existed = Article.objects.filter(url=url).count() > 0
    return JsonResponse(dict(code=requests.codes.ok, existed=existed))
