from django.conf import settings
from wechatpy import WeChatPay


def get_instance():
    return WeChatPay(
        appid=settings.WX_PAY_MP_APP_ID,
        mch_key=settings.WX_PAY_MCH_KEY,
        mch_cert=settings.WX_PAY_MCH_CERT,
        sub_appid=settings.WX_PAY_SUB_APP_ID,
        api_key=settings.WX_PAY_API_KEY,
        mch_id=settings.WX_PAY_MCH_ID,
    )
