import hashlib
import json
import logging
import time

import requests
from django.conf import settings

from downloader.utils import browser


def _get_sign(pd_id, pd_key, timestamp):
    md5 = hashlib.md5()
    md5.update((timestamp + pd_key).encode())
    csign = md5.hexdigest()

    md5 = hashlib.md5()
    md5.update((pd_id + timestamp + csign).encode())
    csign = md5.hexdigest()
    return csign


def predict_code(image: str) -> str | None:
    """
    验证码识别

    :param image:
    :return:
    """

    tm = str(int(time.time()))
    sign = _get_sign(settings.PD_ID, settings.PD_KEY, tm)
    data = {
        "user_id": settings.PD_ID,
        "timestamp": tm,
        "sign": sign,
        "predict_type": 30400,
        "up_type": "mt",
    }
    api = "http://pred.fateadm.com/api/capreg"
    files = {"img_data": ("img_data", open(image, "rb").read())}
    headers = {"user-agent": browser.get_random_ua()}
    # requests POST a Multipart-Encoded File
    # https://requests.readthedocs.io/en/master/user/quickstart/#post-a-multipart-encoded-file
    with requests.post(api, data, files=files, headers=headers) as r:
        if r.status_code != requests.codes.OK:
            logging.error(
                f"code recognition error: {r.status_code} {r.content.decode()}"
            )
            return None

        try:
            res = r.json()
            if res["RetCode"] == "0":
                data = json.loads(res["RspData"])
                code = data["result"]
                return code

            logging.error(f"code recognition error: {r.status_code} {r.text}")
            return None

        except Exception as e:
            logging.error(
                f"code recognition error: {e}, code: {r.status_code}, text: {r.text}"
            )
            return None
