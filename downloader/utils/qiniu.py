from django.conf import settings
from qiniu import Auth, put_file, etag


def qiniu_upload(bucket, local_file, key) -> bool:
    """
    七牛云存储上传文件

    :return:
    """

    q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = q.upload_token(bucket, key, 3600)
    ret, info = put_file(token, key, local_file)
    return ret["key"] == key and ret["hash"] == etag(local_file)


def qiniu_get_url(key: str) -> str:
    return f"http://{settings.QINIU_OPEN_DOMAIN}/{key}"
