# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/18

"""
import os

if __name__ == '__main__':
    path = '/Users/mac/workspace/pycharm/csdnbot/download'
    sub_paths = os.listdir(path)
    for sub_path in sub_paths:
        print(f'{sub_path}: {os.listdir(os.path.join(path, sub_path))}')

