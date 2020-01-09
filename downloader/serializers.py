# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from rest_framework.serializers import ModelSerializer

from downloader.models import User, DownloadRecord, Order


class UserSerializers(ModelSerializer):
    class Meta:
        model = User
        fields = ['create_time', 'email', 'valid_count', 'used_count', 'invite_code']


class DownloadRecordSerializers(ModelSerializer):
    class Meta:
        model = DownloadRecord
        fields = ['create_time', 'resource_url']


class OrderSerializers(ModelSerializer):
    class Meta:
        model = Order
        fields = ['create_time', 'total_amount', 'comment', 'pay_url', 'paid_time']
