import os
import sys

import django
from django.contrib.auth.hashers import make_password

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resium.settings.dev')
django.setup()

import datetime

from downloader.models import User

if __name__ == '__main__':
    uid = '000000'
    t = datetime.datetime.now()
    password = make_password('admin123')
    user = User.objects.create(uid=uid, login_time=t, nickname='admin', password=password,
                               is_admin=True, point=999999, can_download=True)

    print(User.objects.get(uid=uid))
