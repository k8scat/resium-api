import json
import logging
import traceback
from datetime import datetime

from django.conf import settings

from downloader.utils import feishu
from downloader.utils.email import send_email


def alert(msg: str, **kwargs):
    s = "\n".join(
        [
            f"{k}: {json.dumps(v, indent=4, sort_keys=True) if isinstance(v, dict) else v}"
            for k, v in kwargs.items()
        ]
    )
    stack = "".join(traceback.format_stack())
    content = (
        f"msg: {msg}\n"
        f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{s}\n"
        f"stack: {stack}"
    )
    logging.warning(content)
    feishu.send_message(content, user_id=settings.FEISHU_USER_ID)
    send_email(subject=msg, content=content, to_addr=settings.ADMIN_EMAIL)
