# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from rest_framework.serializers import ModelSerializer

from downloader.models import User, DownloadRecord, Order, Service, Resource


class UserSerializers(ModelSerializer):
    class Meta:
        model = User
        fields = ['create_time', 'email', 'valid_count', 'used_count', 'invite_code']


class DownloadRecordSerializers(ModelSerializer):
    class Meta:
        model = DownloadRecord
        fields = ['update_time', 'resource_url', 'title']


class OrderSerializers(ModelSerializer):
    class Meta:
        model = Order
        fields = ['create_time', 'total_amount', 'pay_url', 'paid_time', 'purchase_count']


class ServiceSerializers(ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'total_amount', 'purchase_count']


class ResourceSerializers(ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
