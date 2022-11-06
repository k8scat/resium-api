from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from django.conf import settings


def send_message(phone: str, code: str):
    """
    发送短信

    :param phone: 手机号
    :param code: 验证码
    :return:
    """

    client = AcsClient(
        settings.ALIYUN_ACCESS_KEY_ID, settings.ALIYUN_ACCESS_KEY_SECRET, "cn-hangzhou"
    )

    request = CommonRequest()
    request.set_accept_format("json")
    request.set_domain("dysmsapi.aliyuncs.com")
    request.set_method("POST")
    request.set_protocol_type("https")  # https | http
    request.set_version("2017-05-25")
    request.set_action_name("SendSms")

    request.add_query_param("RegionId", "cn-hangzhou")
    request.add_query_param("PhoneNumbers", phone)
    request.add_query_param("SignName", settings.ALIYUN_SMS_SIGN_NAME)
    request.add_query_param("TemplateCode", settings.ALIYUN_SMS_TEMPLATE_CODE)
    request.add_query_param("TemplateParam", {"code": code})

    client.do_action_with_exception(request)
