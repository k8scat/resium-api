# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import user, service, order, resource, advert, coupon, account, download_record, article, bot, \
    oauth, open


urlpatterns = [
    re_path(r'^wx/?$', user.wx),
    path('get_user/', user.get_user),
    path('reset_has_check_in_today/', user.reset_has_check_in_today),

    path('list_services/', service.list_services),
    path('list_points/', service.list_points),

    path('list_orders/', order.list_orders),
    path('create_order/', order.create_order),
    path('alipay_notify/', order.alipay_notify),
    re_path(r'^delete_order/?$', order.delete_order),

    path('list_coupons/', coupon.list_coupons),

    re_path(r'^check_baidu_cookies/?$', account.check_baidu_cookies),
    re_path(r'^check_csdn_cookies/?$', account.check_csdn_cookies),
    re_path(r'^check_docer_cookies/?$', account.check_docer_cookies),
    re_path(r'^check_qiantu_cookies/?$', account.check_qiantu_cookies),
    re_path(r'^reset_csdn_today_download_count/?$', account.reset_csdn_today_download_count),

    path('list_download_records/', download_record.list_download_records),
    re_path(r'^delete_download_record/?$', download_record.delete_download_record),

    path('oss_download/', resource.oss_download),
    path('download/', resource.download),
    path('upload/', resource.upload),
    re_path(r'^check_file/?$', resource.check_file),
    path('list_uploaded_resources/', resource.list_uploaded_resources),
    re_path(r'^get_resource/?$', resource.get_resource),
    re_path(r'^list_comments/?$', resource.list_comments),
    path('create_comment/', resource.create_comment),
    path('list_resource_tags/', resource.list_resource_tags),
    re_path(r'^list_resources/?$', resource.list_resources),
    path('get_resource_count/', resource.get_resource_count),
    re_path(r'^parse_resource/?$', resource.parse_resource),
    path('check_resource_existed/', resource.check_resource_existed),

    re_path(r'^get_random_advert/?$', advert.get_random_advert),

    path('parse_csdn_article/', article.parse_csdn_article),
    re_path(r'^list_articles/?$', article.list_articles),
    path('get_article_count/', article.get_article_count),
    re_path(r'^get_article/?$', article.get_article),

    path('bot/set_user_can_download/', bot.set_user_can_download),

    re_path(r'^oauth/dev/?$', oauth.dev),
    re_path(r'^oauth/qq/?$', oauth.qq),
    re_path(r'^oauth/github/?$', oauth.github),
    re_path(r'^oauth/gitee/?$', oauth.gitee),
    re_path(r'^oauth/baidu/?$', oauth.baidu),

    path('open/dwz/', open.dwz),
    path('open/download/', open.download)
]

