import json

import requests
from django.conf import settings


def get_short_url(url: str, long_term: bool = False):
    """
    生成短网址

    https://dwz.cn/console/apidoc

    :param url:
    :param long_term
    :return:
    """

    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Token": settings.BAIDU_DWZ_TOKEN,
    }
    body = {"Url": url, "TermOfValidity": "long-term" if long_term else "1-year"}
    api = "https://dwz.cn/admin/v2/create"
    with requests.post(api, data=json.dumps(body), headers=headers) as r:
        if r.status_code == requests.codes.OK and r.json()["Code"] == 0:
            return r.json()["ShortUrl"]

        return None


def get_long_url(url: str):
    """
    还原短网址

    https://dwz.cn/console/apidoc

    :param url:
    :return:
    """

    headers = {"Content-Type": "application/json", "Token": settings.BAIDU_DWZ_TOKEN}
    body = {"shortUrl": url}
    api = "https://dwz.cn/admin/v2/query"
    with requests.post(api, data=json.dumps(body), headers=headers) as r:
        if r.status_code == requests.codes.OK and r.json()["Code"] == 0:
            return r.json()["LongUrl"]

        return None
