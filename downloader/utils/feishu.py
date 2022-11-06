import base64
import hashlib
import json
import logging
from typing import Dict

import requests
from Crypto.Cipher import AES
from django.conf import settings
from django.core.cache import cache


class AESCipher(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode("utf8"))
        if isinstance(data, u_type):
            return data.encode("utf8")
        return data

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]

    def decrypt(self, enc):
        iv = enc[: AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size :]))

    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return self.decrypt(enc).decode("utf8")


def verify_decrypt(encrypt: str) -> Dict:
    cipher = AESCipher(settings.FEISHU_APP_ENCRYPT_KEY)
    decrypt_string = cipher.decrypt_string(encrypt)
    return json.loads(decrypt_string)


def get_tenant_access_token() -> str:
    token = cache.get(settings.FEISHU_TOKEN_CACHE_KEY)
    if token:
        return token

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    payload = {
        "app_id": settings.FEISHU_APP_ID,
        "app_secret": settings.FEISHU_APP_SECRET,
    }
    with requests.post(url, json=payload) as r:
        if r.status_code == requests.codes.ok:
            data = r.json()
            if data.get("code", -1) == 0:
                token = data.get("tenant_access_token", None)
                if token:
                    cache.set(
                        settings.FEISHU_TOKEN_CACHE_KEY,
                        token,
                        timeout=settings.FEISHU_TOKEN_INTERVAL,
                    )
                    return token


def send_message(text, **kwargs):
    """
    ref: https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN
    """
    url = "https://open.feishu.cn/open-apis/message/v4/send/"
    token = get_tenant_access_token()
    headers = {"Authorization": "Bearer " + token}
    payload = {"msg_type": "text", "content": {"text": text}} | kwargs
    with requests.post(url, json=payload, headers=headers) as r:
        if r.status_code == requests.codes.ok:
            logging.error(
                f"failed to send feishu message, code: {r.status_code}, text: {r.text}, payload: {payload}"
            )
