import django_filters
from .models import Car

class CarFilter(django_filters.FilterSet):
    owner_name = django_filters.CharFilter(field_name='owner_name', lookup_expr='icontains')
    plate_number = django_filters.CharFilter(field_name='plate_number', lookup_expr='icontains')

    class Meta:
        model = Car
        fields = ['plate_number', 'owner_name']
