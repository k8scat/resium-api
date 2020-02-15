# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/1/7

"""
from rest_framework import serializers

from downloader.models import *


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'create_time', 'email', 'valid_count', 'used_count']


class DownloadRecordSerializers(serializers.ModelSerializer):
    class Meta:
        model = DownloadRecord
        fields = ['update_time', 'resource_url', 'title']


class OrderSerializers(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['create_time', 'total_amount', 'pay_url', 'paid_time', 'purchase_count']


class ServiceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'total_amount', 'purchase_count']


class ResourceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'


class CouponSerializers(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'


class LoginSerializers(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=100)


class PurchaseSerializers(serializers.Serializer):
    total_amount = serializers.FloatField()
    purchase_count = serializers.IntegerField()
    code = serializers.CharField(max_length=50)


class RegisterSerializers(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=100)
    invited_code = serializers.CharField(max_length=6)


class ResetPasswordSerializers(serializers.Serializer):
    old_password = serializers.CharField(max_length=100)
    new_password = serializers.CharField(max_length=100)

