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
import requests
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from downloader.models import User


def auth(fn):
    @wraps(fn)
    def _wrapper(request: WSGIRequest):
        token = request.headers.get(settings.REQUEST_TOKEN_HEADER)
        if not token:
            return JsonResponse(dict(code=requests.codes.unauthorized, msg="未登录"))

        try:
            pre_len = len(settings.REQUEST_TOKEN_PREFIX)
            token = token[pre_len:]
            # pyjwt 验证 jjwt: http://cn.voidcc.com/question/p-mqbvfvhx-tt.html
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS512"])
        except Exception as e:
            logging.info(f"failed to decode token: {e}")
            return JsonResponse(dict(code=requests.codes.unauthorized, msg="未登录"))

        uid = payload.get("sub", None)
        if not uid or User.objects.filter(uid=uid).count() <= 0:
            return JsonResponse(dict(code=requests.codes.unauthorized, msg="未登录"))

        request.session["uid"] = uid
        logging.info(f"Request by {uid}: {request.get_full_path()}")
        return fn(request)

    return _wrapper
