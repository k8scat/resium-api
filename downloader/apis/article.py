# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/20

"""
import re

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import api_view

from downloader.decorators import auth
from downloader.models import CsdnAccount, Article, User, ArticleComment
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
        article = Article.objects.get(url=article_url)
        return JsonResponse(dict(code=200, article=ArticleSerializers(article).data))

    except Article.DoesNotExist:
        csdn_account = CsdnAccount.objects.get(is_enabled=True)
        headers = {
            'cookie': csdn_account.cookies,
            'user-agent': get_random_ua()
        }
        with requests.get(article_url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.text, 'lxml')
                # VIP文章
                is_vip = len(soup.select('span.vip_article')) > 0
                if not is_vip:
                    return JsonResponse(dict(code=400, msg='非VIP文章'))
                # 文章标题
                title = soup.select('h1.title-article')[0].string
                # 文章作者
                author = soup.select('a.follow-nickName')[0].string
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
                return JsonResponse(dict(code=requests.codes.ok, article=ArticleSerializers(article).data))

            ding(f'文章获取失败: {article_url}',
                 need_email=True,
                 uid=uid,
                 error=r.text)
            return JsonResponse(dict(code=requests.codes.server_error, msg='文章获取失败'))


@api_view()
def list_articles(request):
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 5))
    key = request.GET.get('key', '')
    if page < 1:
        page = 1
    start = count * (page - 1)
    end = start + count
    articles = Article.objects.order_by('-create_time').filter(Q(title__icontains=key) |
                                                               Q(desc__icontains=key) |
                                                               Q(content__icontains=key) |
                                                               Q(tags__icontains=key)).all()[start:end]
    return JsonResponse(dict(code=requests.codes.ok, articles=ArticleSerializers(articles, many=True).data))


@api_view()
def get_article_count(request):
    key = request.GET.get('key', '')
    return JsonResponse(dict(code=requests.codes.ok, count=Article.objects.filter(Q(title__icontains=key) |
                                                                    Q(desc__icontains=key) |
                                                                    Q(tags__icontains=key) |
                                                                    Q(content__icontains=key)).count()))


@api_view()
def get_article(request):
    try:
        article_id = request.GET.get('id', None)
        if not article_id:
            return JsonResponse(dict(code=requests.codes.bad_request, msg='错误的请求'))
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
        article_comment = ArticleComment.objects.create(user=user, resource=article, content=content)
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
        comments = ArticleComment.objects.filter(article=article).all()
        return JsonResponse(dict(code=requests.codes.ok,
                                 comments=ArticleCommentSerializers(comments, many=True).data))
    except Article.DoesNotExist:
        return JsonResponse(dict(code=requests.codes.not_found,
                                 msg='文章不存在'))

