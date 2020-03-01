# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/29

"""
import os
import re

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csdnbot.settings.dev')
django.setup()
from downloader.models import Student

from django.conf import settings
from xlrd import open_workbook

if __name__ == '__main__':
    path = os.path.join(settings.BASE_DIR, 'NCU_students_info')
    files = os.listdir(path)
    for file in files:
        cls = file.split('.')[0]  # 班级
        grade = int('20' + re.findall(r'\d{2}', file)[0])  # 年级
        major = re.findall(r'\w{4}', file)[0]
        college = '软件学院'

        file = os.path.join(path, file)
        book = open_workbook(file)
        sheet = book.sheet_by_index(0)

        for row_index in range(2, sheet.nrows):
            sid = sheet.cell(row_index, 1).value
            if not sid:
                continue
            name = sheet.cell(row_index, 2).value
            try:
                Student(grade=grade, name=name, sid=sid, cls=cls, major=major, college=college).save()
            except Exception:
                continue


