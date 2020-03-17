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
        fields = ['id', 'create_time', 'email', 'point', 'used_point', 'nickname']


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
        fields = ['id', 'create_time', 'resource_url', 'title', 'resource_id', 'used_point']


class OrderSerializers(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'create_time', 'total_amount', 'pay_url', 'has_paid', 'point']


class ServiceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'total_amount', 'point']


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


