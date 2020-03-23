# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/26

https://github.com/adamchainz/django-cors-headers/issues/495

"""
from django.utils.deprecation import MiddlewareMixin


class CorsMiddleware(MiddlewareMixin):
    """
    解决cors问题

    Todo: django-cors-headers 没有在请求头添加 Access-Control-Allow-Origin

    """

    def process_response(self, request, response):
        response['Access-Control-Allow-Origin'] = '*'
        return response


