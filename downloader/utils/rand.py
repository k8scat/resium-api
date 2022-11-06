import random
import string
import uuid as _uuid

from downloader.models import User


def get_random_str(n: int, source: str | None = None) -> str:
    if not source:
        source = string.digits + string.ascii_letters
    return "".join(random.sample(source, n))


def uuid():
    """
    通过uuid获取唯一字符串

    :return:
    """

    return str(_uuid.uuid1()).replace("-", "")


def get_random_int(n: int = 6) -> str:
    return "".join(random.sample(string.digits, n))


def gen_uid(n: int = 6) -> str:
    while True:
        uid = get_random_int(n)
        if User.objects.filter(uid=uid).count() == 0:
            return uid
