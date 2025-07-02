from rest_framework import viewsets, filters, permissions, serializers
from .models import Car, JobEntry, Service, CarServiceRecord, InventoryUsage
from .serializers import CarSerializer, JobEntrySerializer, ServiceSerializer, CarServiceRecordSerializer, InventoryUsageSerializer
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from rest_framework.decorators import action
from django.utils.dateparse import parse_date
from django.db.models import Sum
from rest_framework.response import Response
from .filters import CarFilter

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
    filterset_class = CarFilter
    search_fields = ['plate_number', 'owner_name', 'model', 'brand']
    ordering_fields = ['plate_number', 'owner_name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


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
    
@extend_schema(tags=["Inventory Usage"])
class InventoryUsageViewSet(viewsets.ModelViewSet):
    queryset = InventoryUsage.objects.all()
    serializer_class = InventoryUsageSerializer
    permission_classes = [permissions.IsAuthenticated]  # or your custom permission
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['service_record', 'product', 'used_at']
    ordering_fields = ['used_at', 'quantity_used']
    search_fields = ['product__name']


    def perform_create(self, serializer):
        usage = serializer.save()
        # Update product stock
        product = usage.product
        if product.quantity_in_stock < usage.quantity_used:
            raise serializers.ValidationError("Not enough stock!")
        product.quantity_in_stock -= usage.quantity_used
        product.save()
    @extend_schema(
    summary="Get usage summary",
    tags=["Inventory Usage"],
    parameters=[
        OpenApiParameter(
            name='date_from',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Start date for usage summary filter (YYYY-MM-DD)'
        ),
        OpenApiParameter(
            name='date_to',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='End date for usage summary filter (YYYY-MM-DD)'
        ),
    ]
)
    @action(detail=False, methods=['get'])
    def usage_summary(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        queryset = self.filter_queryset(self.get_queryset())
        if date_from:
            queryset = queryset.filter(used_at__date__gte=parse_date(date_from))
        if date_to:
            queryset = queryset.filter(used_at__date__lte=parse_date(date_to))

        summary = queryset.values('product__name').annotate(total_used=Sum('quantity_used')).order_by('-total_used')
        return Response({
            "status_code": 200,
            "message": "Usage summary generated",
            "description": "Summary of inventory usage by product",
            "data": list(summary)
        })