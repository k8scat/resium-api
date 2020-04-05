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
from downloader.models import CsdnAccount, Article, User
from downloader.serializers import ArticleSerializers
from downloader.utils import ding


@auth
@api_view(['POST'])
def parse_csdn_article(request):
    email = request.session.get('email')
    try:
        user = User.objects.get(email=email, is_active=True)
        point = settings.ARTICLE_POINT
        if user.point < point:
            return JsonResponse(dict(code=400, msg='积分不足，请前往捐赠'))
        if not user.phone:
            return JsonResponse(dict(code=4000, msg='请前往个人中心进行绑定手机号'))
        if not user.can_download:
            return JsonResponse(dict(code=400, msg='错误的请求'))
    except User.DoesNotExist:
        return JsonResponse(dict(code=401, msg='未认证'))

    article_url = request.data.get('url', None)
    if not article_url or not re.match(r'http(s)?://blog\.csdn\.net/.+/article/details/.+$', article_url):
        return JsonResponse(dict(code=400, msg='错误的请求'))

    article_url = article_url.split('?')[0]
    try:
        article = Article.objects.get(url=article_url)
        return JsonResponse(dict(code=200, article=ArticleSerializers(article).data))

    except Article.DoesNotExist:
        csdn_account = CsdnAccount.objects.get(is_enabled=True)
        headers = {
            'cookie': csdn_account.cookies,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        }
        with requests.get(article_url, headers=headers) as r:
            if r.status_code == requests.codes.OK:
                soup = BeautifulSoup(r.text, 'lxml')
                # VIP文章
                is_vip = len(soup.select('span.vip_article')) > 0
                if user.email != 'hsowan.me@gmail.com' and not is_vip:
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
                return JsonResponse(dict(code=200, article=ArticleSerializers(article).data))

            ding(f'文章获取失败: {article_url}')
            return JsonResponse(dict(code=500, msg='文章获取失败'))


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
    return JsonResponse(dict(code=200, articles=ArticleSerializers(articles, many=True).data))


@api_view()
def get_article_count(request):
    key = request.GET.get('key', '')
    return JsonResponse(dict(code=200, count=Article.objects.filter(Q(title__icontains=key) |
                                                                    Q(desc__icontains=key) |
                                                                    Q(tags__icontains=key) |
                                                                    Q(content__icontains=key)).count()))


@api_view()
def get_article(request):
    try:
        article_id = request.GET.get('id', None)
        if not article_id:
            return JsonResponse(dict(code=400, msg='错误的请求'))
        article = Article.objects.get(id=article_id)
        article.view_count += 1
        article.save()
        return JsonResponse(dict(code=200, article=ArticleSerializers(article).data))
    except Article.DoesNotExist:
        return JsonResponse(dict(code=404, msg='博客不存在'))
