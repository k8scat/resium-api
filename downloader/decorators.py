# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/10

decorator:
https://www.liaoxuefeng.com/wiki/1016959663602400/1017451662295584
https://book.pythontips.com/en/latest/decorators.html#decorators-with-arguments
https://foofish.net/python-decorator.html

*args and **kwargs:
https://book.pythontips.com/en/latest/args_and_kwargs.html

@auth必须放在@ratelimit后面，因为@ratelimit用的是HttpRequest，而@auth用的是WSGIRequest

"""
import logging
from functools import wraps

import jwt
from django.conf import settings
from django.http import JsonResponse

from downloader.models import User


def auth(fn):
    @wraps(fn)
    def _wrapper(request):
        # path vs. path_info: https://docs.djangoproject.com/en/3.0/ref/request-response/
        logging.info(f'Auth: {request.path_info}')
        token = request.headers.get(settings.REQUEST_TOKEN_HEADER, None)
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
            logging.info(f'Request by {email}: {request.get_full_path()}')
        else:
            return JsonResponse(dict(code=401, msg='未认证'))
        return fn(request)
    return _wrapper
