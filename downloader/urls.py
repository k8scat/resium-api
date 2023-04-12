from django.urls import path, re_path

from downloader.controllers import resource
from downloader.controllers import (
    user,
    service,
    order,
    advert,
    feishu,
    download_record,
    article,
    notice,
    version,
)

urlpatterns = [
    # user
    path("get_user/", user.get_user),
    re_path(r"^mp_login/?$", user.mp_login),
    path("save_qr_code/", user.save_qr_code),
    path("scan_code/", user.scan_code),
    re_path(r"^check_scan/?$", user.check_scan),
    path("set_password/", user.set_password),
    path("login/", user.login),
    re_path(r"^set_email_with_code/?$", user.set_email_with_code),
    path("request_email_code/", user.request_email_code),
    path("list_point_records/", user.list_point_records),
    re_path(r"^delete_point_record/?$", user.delete_point_record),
    path("request_reset_password/", user.request_reset_password),
    path("reset_password/", user.reset_password),
    # service
    path("list_services/", service.list_services),
    # order
    path("list_orders/", order.list_orders),
    re_path(r"^delete_order/?$", order.delete_order),
    path("mp_pay/", order.mp_pay),
    path("mp_pay_notify/", order.mp_pay_notify),
    # download_record
    path("list_download_records/", download_record.list_download_records),
    re_path(r"^delete_download_record/?$", download_record.delete_download_record),
    # resource
    path("oss_download/", resource.oss_download),
    path("download/", resource.download),
    path("upload/", resource.upload),
    re_path(r"^check_file/?$", resource.check_file),
    path("list_uploaded_resources/", resource.list_uploaded_resources),
    re_path(r"^get_resource/?$", resource.get_resource),
    re_path(r"^list_resource_comments/?$", resource.list_resource_comments),
    path("create_resource_comment/", resource.create_resource_comment),
    path("list_resource_tags/", resource.list_resource_tags),
    re_path(r"^list_resources/?$", resource.list_resources),
    path("get_resource_count/", resource.get_resource_count),
    re_path(r"^parse_resource/?$", resource.parse_resource),
    path("check_resource_existed/", resource.check_resource_existed),
    path("doc_convert/", resource.doc_convert),
    path("check_docer_existed/", resource.check_docer_existed),
    # advert
    re_path(r"^get_random_advert/?$", advert.get_random_advert),
    path("list_mp_swiper_ads/", advert.list_mp_swiper_ads),
    # article
    path("parse_csdn_article/", article.parse_csdn_article),
    re_path(r"^list_articles/?$", article.list_articles),
    path("get_article_count/", article.get_article_count),
    re_path(r"^get_article/?$", article.get_article),
    re_path(r"^list_article_comments/?$", article.list_article_comments),
    path("create_article_comment/", article.create_article_comment),
    # 公告
    path("get_notice/", notice.get_notice),
    path("update_notice/", notice.update_notice),
    # 飞书机器人
    path("feishu_bot/", feishu.bot),
    # 版本
    path("create_version/", version.create_version),
    path("get_version/", version.get_latest_version),
]
