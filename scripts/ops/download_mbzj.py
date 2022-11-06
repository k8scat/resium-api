# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/7/11

"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resium.settings.prod")
django.setup()

import json
from bs4 import BeautifulSoup
from django.conf import settings
from downloader.models import Resource
from time import sleep
import requests
from downloader.utils import get_random_ua


def parse_resources(url):
    headers = {"user-agent": get_random_ua(), "referer": "http://www.cssmoban.com/"}
    with requests.get(url, headers) as r:
        soup = BeautifulSoup(r.content.decode(), "lxml")
        for item in soup.select("ul.thumbItem.large li>a"):
            resource_url = "http://www.cssmoban.com" + item.get("href")
            resources[resource_url] = 0

        next_page_url = (
            soup.find("td", attrs={"id": "pagelist"}).select("a.next")[1].get("href")
        )
        if (
            soup.find("td", attrs={"id": "pagelist"}).select("a.next")[1].get("href")
            != "javascript:;"
        ):
            next_page_url = "http://www.cssmoban.com/wpthemes/" + next_page_url
            parse_resources(next_page_url)


if __name__ == "__main__":
    # resources = {}
    # parse_resources(url='http://www.cssmoban.com/wpthemes/index.shtml')
    # with open('mbzj.json', 'w') as f:
    #     f.write(json.dumps(resources))

    with open("mbzj.json", "r") as f:
        resources = json.loads(f.read())

    for k, v in resources.items():
        if Resource.objects.filter(url=k).count() == 1:
            print("已存在")
            continue

        headers = {
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI2NjY2NjYifQ.hcP4NzJUIigurnA0c1iXmE0H-kYaIogIz-iusKzf1jc1sL6VGm3ejnATQIPVNaB-oAWJSX1_KMKK9_KxvWCGvA"
        }
        data = {"url": k, "point": settings.MBZJ_POINT, "t": "url"}
        with requests.post(
            "https://api.resium.cn/download/", headers=headers, json=data
        ) as r:
            print(r.content)

    with open("mbzj.json", "w") as f:
        f.write(json.dumps(resources))
