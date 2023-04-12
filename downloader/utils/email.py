from typing import List

from django.conf import settings
from django.core.mail import send_mail


def send_email(subject: str, content: str, to_addr: str | List[str]):
    recipient_list = []
    if isinstance(to_addr, str):
        recipient_list = [to_addr]
    elif isinstance(to_addr, list):
        recipient_list = to_addr

    send_mail(
        subject,
        content,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )
