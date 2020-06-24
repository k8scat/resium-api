# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from django.urls import path, re_path
from downloader.apis import user, service, order, resource, advert, account, download_record, article, bot, \
    oauth, ad, system_info

urlpatterns = [
    # user
    re_path(r'^wx/?$', user.wx),
    path('get_user/', user.get_user),
    path('reset_has_check_in_today/', user.reset_has_check_in_today),
    re_path(r'^mp_login/?$', user.mp_login),
    path('save_qr_code/', user.save_qr_code),
    path('scan_code/', user.scan_code),
    re_path(r'^check_scan/?$', user.check_scan),
    path('set_password/', user.set_password),
    path('login/', user.login),
    re_path(r'^check_in/?$', user.check_in),
    re_path(r'^set_email/?$', user.set_email),
    path('request_set_email/', user.request_set_email),
    path('list_point_records/', user.list_point_records),
    re_path(r'^delete_point_record/?$', user.delete_point_record),

    # service
    path('list_services/', service.list_services),
    path('list_points/', service.list_points),

    # order
    path('list_orders/', order.list_orders),
    path('create_order/', order.create_order),
    path('alipay_notify/', order.alipay_notify),
    re_path(r'^delete_order/?$', order.delete_order),
    path('mp_pay/', order.mp_pay),
    path('mp_pay_notify/', order.mp_pay_notify),

    # account
    re_path(r'^check_baidu_cookies/?$', account.check_baidu_cookies),
    re_path(r'^check_csdn_cookies/?$', account.check_csdn_cookies),
    re_path(r'^check_docer_cookies/?$', account.check_docer_cookies),
    re_path(r'^check_qiantu_cookies/?$', account.check_qiantu_cookies),
    re_path(r'^reset_csdn_today_download_count/?$', account.reset_csdn_today_download_count),
    path('add_or_update_csdn_account/', account.add_or_update_csdn_account),
    path('list_csdn_accounts/', account.list_csdn_accounts),
    re_path(r'^remove_csdn_sms_validate/?$', account.remove_csdn_sms_validate),

    # download_record
    path('list_download_records/', download_record.list_download_records),
    re_path(r'^delete_download_record/?$', download_record.delete_download_record),

    # resource
    path('oss_download/', resource.oss_download),
    path('download/', resource.download),
    path('upload/', resource.upload),
    re_path(r'^check_file/?$', resource.check_file),
    path('list_uploaded_resources/', resource.list_uploaded_resources),
    re_path(r'^get_resource/?$', resource.get_resource),
    re_path(r'^list_resource_comments/?$', resource.list_resource_comments),
    path('create_resource_comment/', resource.create_resource_comment),
    path('list_resource_tags/', resource.list_resource_tags),
    re_path(r'^list_resources/?$', resource.list_resources),
    path('get_resource_count/', resource.get_resource_count),
    re_path(r'^parse_resource/?$', resource.parse_resource),
    path('check_resource_existed/', resource.check_resource_existed),
    path('doc_convert/', resource.doc_convert),
    path('get_download_interval/', resource.get_download_interval),
    re_path(r'^list_recommend_resources/?$', resource.list_recommend_resources),

    # advert
    re_path(r'^get_random_advert/?$', advert.get_random_advert),

    # article
    path('parse_csdn_article/', article.parse_csdn_article),
    re_path(r'^list_articles/?$', article.list_articles),
    path('get_article_count/', article.get_article_count),
    re_path(r'^get_article/?$', article.get_article),
    re_path(r'^list_article_comments/?$', article.list_article_comments),
    path('create_article_comment/', article.create_article_comment),
    re_path(r'^list_recommend_articles/?$', article.list_recommend_articles),

    # bot
    path('bot/set_user_can_download/', bot.set_user_can_download),
    path('bot/get_user/', bot.get_user),
    path('bot/set_csdn_sms_validate_code/', bot.set_csdn_sms_validate_code),
    path('bot/list_csdn_accounts/', bot.list_csdn_accounts),
    path('bot/activate_taobao_user/', bot.activate_taobao_user),

    # oauth
    re_path(r'^oauth/dev/?$', oauth.dev),
    re_path(r'^oauth/qq/?$', oauth.qq),
    re_path(r'^oauth/gitee/?$', oauth.gitee),

    # ad
    path('list_mp_swiper_ads/', ad.list_mp_swiper_ads),

    # SystemInfo
    path('get_system_info/', system_info.get_system_info)
]

