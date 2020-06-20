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
        fields = '__all__'


class ResourceSerializers(serializers.ModelSerializer):
    nickname = serializers.CharField(source='user.nickname')
    avatar_url = serializers.CharField(source='user.avatar_url')

    class Meta:
        model = Resource
        fields = ['id', 'create_time', 'desc', 'nickname', 'size', 'is_audited',
                  'tags', 'title', 'filename', 'avatar_url', 'download_count']


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
        fields = ['id', 'total_amount', 'point', 'is_hot']


class ResourceCommentSerializers(serializers.ModelSerializer):
    avatar_url = serializers.CharField(source='user.avatar_url')
    nickname = serializers.CharField(source='user.nickname')

    class Meta:
        model = ResourceComment
        fields = ['id', 'content', 'avatar_url', 'nickname', 'create_time']


class ArticleCommentSerializers(serializers.ModelSerializer):
    avatar_url = serializers.CharField(source='user.avatar_url')
    nickname = serializers.CharField(source='user.nickname')

    class Meta:
        model = ArticleComment
        fields = ['id', 'content', 'avatar_url', 'nickname', 'create_time']


class AdvertSerializers(serializers.ModelSerializer):
    class Meta:
        model = Advert
        fields = '__all__'


class ArticleSerializers(serializers.ModelSerializer):
    nickname = serializers.CharField(source='user.nickname')
    avatar_url = serializers.CharField(source='user.avatar_url')

    class Meta:
        model = Article
        fields = ['id', 'create_time', 'desc', 'nickname', 'title', 'content',
                  'tags', 'avatar_url', 'view_count', 'author', 'is_vip', 'url',
                  'is_original']


class CsdnAccountSerializers(serializers.ModelSerializer):
    class Meta:
        model = CsdnAccount
        fields = ['id', 'csdn_id', 'update_time', 'is_enabled', 'is_disabled',
                  'valid_count', 'used_count',
                  'today_download_count', 'need_sms_validate', 'is_cookies_valid']


class UploadRecordSerializers(serializers.ModelSerializer):
    title = serializers.CharField(source='resource.title')
    is_audited = serializers.IntegerField(source='resource.is_audited')

    class Meta:
        model = UploadRecord
        fields = ['id', 'create_time', 'title', 'is_audited']


class PointRecordSerializers(serializers.ModelSerializer):
    class Meta:
        model = PointRecord
        fields = '__all__'


class MpSwiperAdSerializers(serializers.ModelSerializer):
    class Meta:
        model = MpSwiperAd
        fields = '__all__'


class SystemInfoSerializers(serializers.ModelSerializer):
    class Meta:
        model = SystemInfo
        fields = '__all__'
