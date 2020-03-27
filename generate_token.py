# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/26

"""
from resium.settings.base import JWT_SECRET
import jwt

if __name__ == '__main__':
    payload = {
        'sub': 'hsowan.me@gmail.com'
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS512').decode()
    print(token)
