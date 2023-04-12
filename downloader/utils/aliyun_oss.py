import os
from typing import List

import oss2
from django.conf import settings
from oss2 import SizedFileAdapter, determine_part_size
from oss2.exceptions import NoSuchKey
from oss2.models import PartInfo


def get_bucket():
    # 阿里云主账号AccessKey拥有所有API的访问权限，风险很高。强烈建议您创建并使用RAM账号进行API访问或日常运维，请登录 https://ram.console.aliyun.com 创建RAM账号。
    auth = oss2.Auth(settings.ALIYUN_ACCESS_KEY_ID, settings.ALIYUN_ACCESS_KEY_SECRET)
    # Endpoint以杭州为例，其它Region请按实际情况填写。
    bucket = oss2.Bucket(
        auth, settings.ALIYUN_OSS_END_POINT, settings.ALIYUN_OSS_BUCKET_NAME
    )

    return bucket


def upload(filepath: str, key: str):
    """
    阿里云 OSS 上传

    参考: https://help.aliyun.com/document_detail/88434.html?spm=a2c4g.11186623.6.849.de955fffeknceQ

    :param filepath: 文件路径
    :param key: 保存在oss上的文件名
    :return:
    """

    bucket = get_bucket()

    # 初始化分片。
    # 如果需要在初始化分片时设置文件存储类型，请在init_multipart_upload中设置相关headers，参考如下。
    # headers = dict()
    # headers["x-oss-storage-class"] = "Standard"
    # upload_id = bucket.init_multipart_upload(key, headers=headers).upload_id
    upload_id = bucket.init_multipart_upload(key).upload_id
    parts = []

    total_size = os.path.getsize(filepath)
    # determine_part_size方法用来确定分片大小。1000KB
    part_size = determine_part_size(total_size, preferred_size=1000 * 1024)

    # 逐个上传分片。
    with open(filepath, "rb") as f:
        part_number = 1
        offset = 0
        while offset < total_size:
            # logging.info('Uploading')
            num_to_upload = min(part_size, total_size - offset)
            # SizedFileAdapter(f, size)方法会生成一个新的文件对象，重新计算起始追加位置。
            result = bucket.upload_part(
                key, upload_id, part_number, SizedFileAdapter(f, num_to_upload)
            )
            parts.append(PartInfo(part_number, result.etag))
            offset += num_to_upload
            part_number += 1

            # print(f"上传进度: {offset / total_size * 100}%")

        # 完成分片上传。
        # 如果需要在完成分片上传时设置文件访问权限ACL，请在complete_multipart_upload函数中设置相关headers，参考如下。
        # headers = dict()
        # headers["x-oss-object-acl"] = oss2.OBJECT_ACL_PRIVATE
        # bucket.complete_multipart_upload(key, upload_id, parts, headers=headers)
        bucket.complete_multipart_upload(key, upload_id, parts)


def get_file(key):
    """
    获取阿里云 OSS 上的文件
    bucket.get_object的返回值是一个类文件对象（File-Like Object）

    参考: https://help.aliyun.com/document_detail/88441.html?spm=a2c4g.11186623.6.854.252f6beeASG3vx

    :param key:
    :return: 类文件对象（File-Like Object）
    """

    bucket = get_bucket()
    return bucket.get_object(key)


def check_file(key):
    """
    判断文件是否存在

    参考: https://help.aliyun.com/document_detail/88454.html?spm=a2c4g.11186623.6.861.321b3557YkGK3S

    :param key:
    :return:
    """
    bucket = get_bucket()
    try:
        return bucket.object_exists(key)
    except NoSuchKey:
        return None


def sign_url(key, expire=3600):
    """
    获取文件临时下载链接，使用签名URL进行临时授权

    参考: https://help.aliyun.com/document_detail/32033.html?spm=a2c4g.11186623.6.881.603f16950kd10U

    :param key:
    :param expire: 默认60*60, 即1小时后过期
    :return:
    """

    bucket = get_bucket()
    return bucket.sign_url("GET", key, expire)


def delete_files(keys: List[str]):
    """
    批量删除OSS上的文件

    :param keys:
    :return:
    """

    bucket = get_bucket()
    # 批量删除3个文件。每次最多删除1000个文件。
    result = bucket.batch_delete_objects(keys)
    # 打印成功删除的文件名。
    # print("\n".join(result.deleted_keys))


def aliyun_oss_delete_file(key: str):
    bucket = get_bucket()

    # 删除文件。<yourObjectName>表示删除OSS文件时需要指定包含文件后缀在内的完整路径，例如abc/efg/123.jpg。
    # 如需删除文件夹，请将<yourObjectName>设置为对应的文件夹名称。如果文件夹非空，则需要将文件夹下的所有object删除后才能删除该文件夹。
    bucket.delete_object(key)
