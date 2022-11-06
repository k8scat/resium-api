import json
import logging
import re

from django.conf import settings
from django.http import JsonResponse
from django.http.response import HttpResponse
from rest_framework.decorators import api_view

from downloader.models import User, Resource
from downloader.serializers import UserSerializers
from downloader.utils import feishu


@api_view(["POST"])
def bot(request):
    encrypt = request.data.get("encrypt", "")
    data = feishu.verify_decrypt(encrypt)
    token = data.get("token", "")
    # 验证事件来源
    if token != settings.FEISHU_APP_VERIFICATION_TOKEN:
        logging.error(f"invalid token: {data}")
        return HttpResponse("")

    logging.info(f"feishu callback: {data}")
    # 事件类型
    feishu_request_type = data.get("type", "")
    if feishu_request_type == "url_verification":
        challenge = data.get("challenge", "")
        return JsonResponse(dict(challenge=challenge))

    if feishu_request_type == "event_callback":
        # 获取事件内容和类型，并进行相应处理，此处只关注给机器人推送的消息事件
        event = data.get("event")
        if event.get("type", "") == "message":
            msg_type = event.get("msg_type", "")
            if msg_type == "text":
                msg_content = event.get("text_without_at_bot", "").strip()
                logging.info(f"got feishu msg_content={msg_content}")

                if re.match(
                    r"^user \d{6}$", msg_content, flags=re.IGNORECASE
                ):  # 查看用户信息
                    uid = msg_content.split(" ")[1]
                    content = get_user(uid)

                # 检查资源是否存在
                elif re.match(
                    r"^resource (http(s)?://download\.csdn\.net/(download|detail)/).+/\d+.*$",
                    msg_content,
                ):
                    url = msg_content.split("?")[0]
                    if Resource.objects.filter(url=url).count() == 0:
                        content = "资源不存在"
                        feishu.send_message(url, user_id=settings.FEISHU_USER_ID)
                    else:
                        content = "资源已存在"

                elif re.match(r"^help$", msg_content, flags=re.IGNORECASE):
                    content = (
                        "- 查看用户: user <uid>"
                        "- 上传资源: upload <file_key> <resource_url>"
                        "- 检查资源是否存在: resource <resource_url>"
                        "- 帮助说明: help"
                    )
                else:
                    content = None

            elif msg_type == "file":
                file_key = event.get("file_key", None)
                content = file_key

            else:
                content = f"暂不支持该消息类型: {msg_type}"

            if content:
                feishu.send_message(content, user_id=settings.FEISHU_USER_ID)

    return HttpResponse("")


def get_user(uid):
    try:
        user = User.objects.get(uid=uid)
        return json.dumps(UserSerializers(user).data)
    except User.DoesNotExist:
        return "用户不存在"
