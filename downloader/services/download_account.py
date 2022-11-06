from downloader.models import CsdnAccount
from downloader.utils import ding


def use_specified_csdn_account(csdn_id=""):
    csdn_account = CsdnAccount.objects.get(csdn_id=csdn_id)
    if csdn_account is None:
        ding(f"[CSDN] 指定账号不存在: {csdn_id}")
        return False
    try:
        CsdnAccount.objects.exclude(csdn_id=csdn_id).update(is_enabled=0)
        csdn_account.is_enabled = 1
        csdn_account.save()
        return True
    except Exception as e:
        ding("[CSDN] 使用指定账号失败", error=e)
        return False
