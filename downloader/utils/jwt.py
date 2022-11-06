import datetime

import jwt
from django.conf import settings


def gen_jwt(uid, expire_seconds=86400):
    """
    生成token

    :param uid:
    :param expire_seconds: 默认1天过期
    :return:
    """

    payload = {"sub": uid}
    if expire_seconds > 0:
        exp = datetime.datetime.utcnow() + datetime.timedelta(seconds=expire_seconds)
        payload.setdefault("exp", exp)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS512").decode()
