import base64
import hashlib
import hmac
import logging
import time
from urllib import parse

import requests
from django.conf import settings


def send_message(msg: str, **kwargs):
    timestamp = round(time.time() * 1000)
    secret_enc = settings.DINGTALK_SECRET.encode("utf-8")
    string_to_sign = f"{timestamp}\n{settings.DINGTALK_SECRET}"
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(
        secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
    ).digest()
    sign = parse.quote_plus(base64.b64encode(hmac_code))

    at_mobiles = kwargs.get("at_mobiles", [])
    is_at_all = kwargs.get("is_at_all", False)

    payload = {
        "msgtype": "text",
        "text": {"content": msg},
        "at": {"atMobiles": at_mobiles, "isAtAll": is_at_all},
    }
    params = {
        "access_token": settings.DINGTALK_ACCESS_TOKEN,
        "timestamp": timestamp,
        "sign": sign,
    }
    dingtalk_api = f"https://oapi.dingtalk.com/robot/send"
    with requests.post(dingtalk_api, json=payload, params=params, verify=False) as r:
        if r.status_code != requests.codes.ok:
            logging.error(
                f"failed to send dingtalk message, code: {r.status_code}, text: {r.text}, payload: {payload}"
            )
