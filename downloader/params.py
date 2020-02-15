# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/9

"""
from drf_yasg import openapi

page = openapi.Parameter('page', openapi.IN_QUERY, description='页码', required=False, type=openapi.TYPE_INTEGER)
key = openapi.Parameter('key', openapi.IN_QUERY, description='关键字', required=False, type=openapi.TYPE_STRING)
resource_url = openapi.Parameter('url', openapi.IN_QUERY, description="资源地址", type=openapi.TYPE_STRING)
resource_key = openapi.Parameter('key', openapi.IN_QUERY, description='资源存储在OSS上的名称', type=openapi.TYPE_STRING)
email = openapi.Parameter('email', openapi.IN_QUERY, description='邮箱', required=True, type=openapi.TYPE_STRING)
code = openapi.Parameter('code', openapi.IN_QUERY, description='验证码', required=True, type=openapi.TYPE_STRING)
temp_password = openapi.Parameter('token', openapi.IN_QUERY, description='加密的临时密码', required=True, type=openapi.TYPE_STRING)
file_md5 = openapi.Parameter('hash', openapi.IN_QUERY, description='文件的md5值', required=True, type=openapi.TYPE_STRING)
