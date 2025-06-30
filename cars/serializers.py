# cars/serializers.py

from rest_framework import serializers
from .models import Car, JobEntry, Service, CarServiceRecord, InventoryUsage

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = '__all__'

class JobEntrySerializer(serializers.ModelSerializer):
    car = CarSerializer(read_only=True)
    car_id = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), source='car', write_only=True)

    class Meta:
        model = JobEntry
        fields = ['id', 'car', 'car_id', 'manual_book_number', 'entry_date', 'notes']
        

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class CarServiceRecordSerializer(serializers.ModelSerializer):
    car = CarSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    car_id = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), write_only=True, source='car')
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), write_only=True, source='service')

    class Meta:
        model = CarServiceRecord
        fields = ['id', 'car', 'service', 'car_id','discount','amount_paid', 'service_id', 'performed_at']
        
        
class InventoryUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryUsage
        fields = ['id', 'service_record', 'product', 'quantity_used', 'used_at']
        read_only_fields = ['id', 'used_at']

