# cars/serializers.py
from django.utils.timezone import now
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
    car = CarSerializer()  # Accept nested car data

    class Meta:
        model = JobEntry
        fields = ['id', 'car', 'manual_book_number', 'entry_date', 'notes', 'created_by', 'entered_by']
        read_only_fields = ['created_by', 'entry_date']

    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

    def create(self, validated_data):
        car_data = validated_data.pop('car')
        plate_number = car_data.get('plate_number')
        user = self.context['request'].user

        try:
            car = Car.objects.get(plate_number=plate_number)
        except Car.DoesNotExist:
            car = Car.objects.create(**car_data, created_by=user)
        job_entry = JobEntry.objects.create(car=car, created_by=user, **validated_data)
        return job_entry
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
        fields = ['id', 'car', 'service', 'car_id','discount','amount_paid', 'service_id', 'performed_at','created_by','entered_by']
        
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"
        
        
class InventoryUsageSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    class Meta:
        model = InventoryUsage
        fields = ['id', 'service_record', 'product', 'quantity_used', 'used_at','created_by','entered_by']
        read_only_fields = ['id', 'used_at','created_by']
    
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"
