# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/26

"""
from resium.settings.base import JWT_SECRET
import jwt

if __name__ == '__main__':
    payload = {
        'sub': '6c148b2a7fef11ea96490242c0a84002.1587047687.5418773'
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS512').decode()
    print(token)
