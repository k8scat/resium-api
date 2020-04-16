# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/4/5

"""
from django.http import HttpResponse
from rest_framework.decorators import api_view


@api_view()
def qq(request):
    return HttpResponse('oauth qq')


@api_view()
def github(request):
    return HttpResponse('oauth github')


@api_view()
def gitee(request):
    return HttpResponse('oauth gitee')

