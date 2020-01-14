# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
import logging
import time

import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from downloader.models import User


class AuthMiddleware(MiddlewareMixin):
    """
    JWT Token Auth Middleware

    Request and response objects: https://docs.djangoproject.com/en/2.2/ref/request-response/
    """
    def process_request(self, request):
        if settings.AUTH_PATHS.count(request.path) == 1:
            logging.info(f'Auth: {request.path}')
            token = request.headers.get(settings.REQUEST_TOKEN_HEADER, None)
            logging.info(token)
            if token is None:
                return JsonResponse(dict(code=401, msg='未认证'))

            try:
                token = token[len(settings.REQUEST_TOKEN_PREFIX):]
                # pyjwt 验证 jjwt: http://cn.voidcc.com/question/p-mqbvfvhx-tt.html
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS512'])
            except Exception as e:
                logging.info(e)
                return JsonResponse(dict(code=401, msg='未认证'))

            email = payload.get('sub', None)
            if email is not None:
                request.session['email'] = email
            else:
                return JsonResponse(dict(code=401, msg='未认证'))
