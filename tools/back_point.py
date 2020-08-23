import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.prod')
django.setup()

import re
from downloader.models import User
from downloader.utils import send_email

if __name__ == '__main__':
    uid = input('uid: ')
    if not re.match(r'^\d{6}$', uid):
        print(r'uid not match pattern: ^\d{6}$')
        exit(1)
    else:
        print(f'uid: {uid}')
    try:
        point = int(input('point: '))
        print(f'point: {point}')

        try:
            user = User.objects.get(uid=uid)
            if not user.can_download:
                print(f'user cannot download: {uid}')
            user.point += point
            user.save()
            print('back point ok')

            if user.email:
                subject = '积分退还通知'
                content = f'积分(${point}积分)已退还至您的账号，请注意查收！如有疑问，请联系admin@resium.cn，感谢支持源自下载！'
                send_email(subject, content, user.email)
                print('email notified ok')
            else:
                print('user not set email')
        except User.DoesNotExist:
            print(f'user not exists: {uid}')
            exit(1)
    except ValueError as e:
        print(e)
        exit(1)

