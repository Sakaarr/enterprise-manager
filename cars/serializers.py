# cars/serializers.py

from rest_framework import serializers
from .models import Car, JobEntry

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
