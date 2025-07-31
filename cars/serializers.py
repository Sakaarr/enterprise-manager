# cars/serializers.py
from django.utils.timezone import now
from rest_framework import serializers
from .models import Car, JobEntry, Service, CarServiceRecord, InventoryUsage, ServiceEntry

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
    
    def update(self, instance, validated_data):
        car_data = validated_data.pop('car', None)
        if car_data:
            car = instance.car
            for attr, value in car_data.items():
                setattr(car, attr, value)
            car.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

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
    
    class Meta:
        model = Service
        read_only_fields = ['created_by']
        fields = '__all__'
        
        
        
    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

class ServiceEntrySerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), write_only=True, source='service')

    class Meta:
        model = ServiceEntry
        fields = ['id', 'service', 'service_id', 'performed_at', 'remarks', 'created_by', 'entered_by']

    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

class CarServiceRecordSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    car = CarSerializer(read_only=True)
    service_entries = ServiceEntrySerializer(many=True, read_only=True)
    car_id = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), write_only=True, source='car')
    
    # Fields for adding new service entries
    services = serializers.ListField(
        child=serializers.DictField(), 
        write_only=True, 
        required=False,
        help_text="List of services to add: [{'service_id': 1, 'remarks': 'optional'}]"
    )

    class Meta:
        model = CarServiceRecord
        fields = ['id', 'car', 'car_id', 'service_entries', 'services', 'created_at', 'updated_at', 'created_by', 'entered_by']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        car = validated_data.pop('car')
        
        # Get or create service record for the car
        service_record, created = CarServiceRecord.objects.get_or_create(
            car=car,
            defaults={'created_by': self.context['request'].user}
        )
        
        # Add new service entries
        for service_data in services_data:
            ServiceEntry.objects.create(
                service_record=service_record,
                service_id=service_data['service_id'],
                remarks=service_data.get('remarks', ''),
                created_by=self.context['request'].user
            )
        
        return service_record

    def update(self, instance, validated_data):
        services_data = validated_data.pop('services', [])
        
        # Add new service entries
        for service_data in services_data:
            ServiceEntry.objects.create(
                service_record=instance,
                service_id=service_data['service_id'],
                remarks=service_data.get('remarks', ''),
                created_by=self.context['request'].user
            )
        
        return instance

        
        
class InventoryUsageSerializer(serializers.ModelSerializer):
    entered_by = serializers.SerializerMethodField()
    car_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = InventoryUsage
        fields = [
            'id', 'product', 'quantity_used', 'used_at',
            'created_by', 'entered_by', 'car_id'
        ]
        read_only_fields = ['id', 'used_at', 'created_by']

    def get_entered_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else "Unknown"

    def create(self, validated_data):
        car_id = validated_data.pop('car_id')

        # Find the latest matching service record for the car
        service_record = CarServiceRecord.objects.filter(
            car_id=car_id
        ).order_by('-id').first()

        if not service_record:
            raise serializers.ValidationError("No service record found for this car.")

        validated_data['service_record'] = service_record

        request = self.context.get("request")
        if request and request.user and not validated_data.get("created_by"):
            validated_data["created_by"] = request.user

        return super().create(validated_data)