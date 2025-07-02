# cars/serializers.py

from rest_framework import serializers
from .models import Car, JobEntry, Service, CarServiceRecord, InventoryUsage

class CarSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    class Meta:
        model = Car
        fields = '__all__'
        read_only_fields = ['created_by']
        
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

class JobEntrySerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    car = CarSerializer(read_only=True)
    car_id = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), source='car', write_only=True)
    read_only_fields = ['created_by']

    class Meta:
        model = JobEntry
        fields = ['id', 'car', 'car_id', 'manual_book_number', 'entry_date', 'notes','created_by']
        
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"
class ServiceSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    read_only_fields = ['created_by']
    class Meta:
        model = Service
        fields = '__all__'
        
        
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

class CarServiceRecordSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    car = CarSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    car_id = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), write_only=True, source='car')
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), write_only=True, source='service')
    read_only_fields = ['created_by']

    class Meta:
        model = CarServiceRecord
        fields = ['id', 'car', 'service', 'car_id','discount','amount_paid', 'service_id', 'performed_at','created_by']
        
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"
        
        
class InventoryUsageSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    class Meta:
        model = InventoryUsage
        fields = ['id', 'service_record', 'product', 'quantity_used', 'used_at','created_by']
        read_only_fields = ['id', 'used_at','created_by']

