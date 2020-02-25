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
        fields = ['id', 'create_time', 'email', 'valid_count', 'used_count', 'nickname']


class ResourceSerializers(serializers.ModelSerializer):
    nickname = serializers.CharField(source='user.nickname')

    class Meta:
        model = Resource
        fields = '__all__'


class DownloadRecordSerializers(serializers.ModelSerializer):
    resource_url = serializers.CharField(source='resource.url')
    title = serializers.CharField(source='resource.title')
    resource_id = serializers.IntegerField(source='resource.id')

    class Meta:
        model = DownloadRecord
        fields = ['id', 'update_time', 'resource_url', 'title', 'resource_id']


class OrderSerializers(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'create_time', 'total_amount', 'pay_url', 'paid_time', 'purchase_count']


class ServiceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'total_amount', 'purchase_count']


class CouponSerializers(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'


class ResourceCommentSerializers(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email')
    nickname = serializers.CharField(source='user.nickname')

    class Meta:
        model = ResourceComment
        fields = ['id', 'content', 'email', 'nickname', 'create_time']


class AdvertSerializers(serializers.ModelSerializer):
    class Meta:
        model = Advert
        fields = '__all__'


