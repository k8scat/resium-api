# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/3/10

生成随机注册码

"""
import random
import string


if __name__ == '__main__':
    print(''.join(random.sample(string.digits, 8)))
