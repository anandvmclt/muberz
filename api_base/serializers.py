from django.contrib.auth.models import User
from rest_framework import serializers
from api_base.models import Commodity, Service, TransferType


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = ['id', 'item_name', 'volume', 'image', 'charge', 'material_type', 'is_plugable']


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'service_from', 'service_to', 'is_plugable']


class TransferTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferType
        fields = ['id', 'transfer_from', 'transfer_to', 'charge']

# class AccountSerializer(serializers.ModelSerializer):
