import logging
import traceback
from datetime import datetime

from django.conf import settings

from downloader.utils import feishu
from downloader.utils.email import send_email


def alert(msg: str, **kwargs):
    s = "\n".join([f"{k}: {v}" for k, v in kwargs.items()])
    content = (
        f"msg: {msg}\n"
        f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{s}\n"
        f"trace: {traceback.format_exc()}"
    )
    logging.warning(content)
    feishu.send_message(content)
    send_email(subject=msg, content=content, to_addr=settings.ADMIN_EMAIL)
