import os
import random
import time


def get_random_ua():
    """
    随机获取User-Agent

    :return:
    """

    ua_list = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
        # Google Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/82.0.4083.0 Safari/537.36 Edg/82.0.456.0",
        # Microsoft Edge
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15",
        # Safari
        # Firefox
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:74.0) Gecko/20100101 Firefox/74.0",
    ]
    return random.choice(ua_list)


def check_download(folder: str, timeout: int = 600) -> str | None:
    t1 = time.time()
    while True:
        if time.time() - t1 > timeout:
            return None

        files = os.listdir(folder)
        if len(files) == 0:
            time.sleep(1)
            continue

        if files[0].endswith(".crdownload"):
            time.sleep(0.1)
            continue

        break

    if len(files) == 0:
        return None

    filename = files[0]
    if filename.endswith(".crdownload"):
        return None

    return filename
