from rest_framework import viewsets, filters
from .models import Car, JobEntry, Service, CarServiceRecord
from .serializers import CarSerializer, JobEntrySerializer, ServiceSerializer, CarServiceRecordSerializer
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema


@extend_schema_view(
    list=extend_schema(tags=["Car"]),
    create=extend_schema(tags=["Car"]),
    retrieve=extend_schema(tags=["Car"]),
    update=extend_schema(tags=["Car"]),
    partial_update=extend_schema(tags=["Car"]),
    destroy=extend_schema(tags=["Car"]),
)
class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['plate_number', 'owner_name']
    search_fields = ['plate_number', 'owner_name', 'model', 'brand']
    ordering_fields = ['plate_number', 'owner_name']


@extend_schema_view(
    list=extend_schema(tags=["JobEntry"]),
    create=extend_schema(tags=["JobEntry"]),
    retrieve=extend_schema(tags=["JobEntry"]),
    update=extend_schema(tags=["JobEntry"]),
    partial_update=extend_schema(tags=["JobEntry"]),
    destroy=extend_schema(tags=["JobEntry"]),
)
class JobEntryViewSet(viewsets.ModelViewSet):
    queryset = JobEntry.objects.all()
    serializer_class = JobEntrySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'car__plate_number': ['exact'],
        'car__owner_name': ['icontains'],
        'entry_date': ['date', 'date__gte', 'date__lte'],
    }
    ordering_fields = ['entry_date', 'manual_book_number']


@extend_schema(tags=["Services"])
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'standard_rate']

    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'partial_update']:
    #         return [IsAuthenticated]
    #     return super().get_permissions()

@extend_schema(tags=["Car Service Records"])
class CarServiceRecordViewSet(viewsets.ModelViewSet):
    queryset = CarServiceRecord.objects.all().select_related('car', 'service')
    serializer_class = CarServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['car__plate_number', 'car__owner_name']
    ordering_fields = ['service_date', 'car__plate_number']

    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'partial_update']:
    #         return [IsAuthenticated]
    #     return super().get_permissions()