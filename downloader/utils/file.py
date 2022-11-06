import hashlib
import os
import uuid
import zipfile

from django.conf import settings


def md5(f):
    m = hashlib.md5()
    while True:
        data = f.read(1024)
        if not data:
            break
        m.update(data)
    return m.hexdigest()


def zip_file(filepath):
    """
    压缩文件夹

    :param filepath: 需要压缩的文件
    :return:
    """

    outfile = os.path.join(settings.DOWNLOAD_DIR, str(uuid.uuid1()) + ".zip")
    files = [filepath, os.path.join(settings.DOWNLOAD_DIR, ".gitkeep")]
    f = zipfile.ZipFile(outfile, "w", zipfile.zlib.DEFLATED)
    for file in files:
        filename = os.path.basename(file)
        f.write(file, filename)
    f.close()
    return outfile
