import logging
from typing import Dict

import requests

from downloader.utils import browser


def get_account_info(cookie: str) -> Dict | None:
    headers = {
        "cookie": cookie,
        "user-agent": browser.get_random_ua(),
        "referer": "https://download.csdn.net/",
    }
    api = "https://download.csdn.net/api/source/index/v1/loginInfo"
    with requests.get(api, headers=headers) as r:
        if r.status_code != requests.codes.ok:
            logging.error(
                f"failed to get csdn vip valid count, code: {r.status_code}, text: {r.text}"
            )
            return None

        try:
            return r.json()

        except Exception as e:
            logging.error(
                f"failed to get csdn vip valid count, code: {r.status_code}, text: {r.text}, exception: {e}"
            )
            return None
