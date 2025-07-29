from rest_framework import viewsets, filters, permissions, serializers
from .models import Car, JobEntry, Service, CarServiceRecord, InventoryUsage, ServiceEntry
from .serializers import CarSerializer, JobEntrySerializer, ServiceSerializer, CarServiceRecordSerializer, InventoryUsageSerializer, ServiceEntrySerializer
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from rest_framework.decorators import action
from django.utils.dateparse import parse_date
from django.db.models import Sum
from rest_framework.response import Response
from .filters import CarFilter
from common.viewsets import StandardizedModelViewSet
from drf_spectacular.types import OpenApiTypes
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

@extend_schema(tags=["Services"])
class ServiceViewSet(StandardizedModelViewSet):
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
class CarServiceRecordViewSet(StandardizedModelViewSet):
    queryset = CarServiceRecord.objects.all().select_related('car').prefetch_related('service_entries__service')
    serializer_class = CarServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['car__plate_number', 'car__owner_name']
    ordering_fields = ['created_at', 'car__plate_number']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        methods=['post'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'service_id': {'type': 'integer'},
                    'remarks': {'type': 'string', 'required': False}
                }
            }
        },
        responses={200: ServiceEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def add_service(self, request, pk=None):
        """Add a new service entry to existing car service record"""
        try:
            # Debug: Print the pk value
            print(f"Looking for CarServiceRecord with pk: {pk}")
            
            # Try to get the object with explicit error handling
            try:
                service_record = CarServiceRecord.objects.select_related('car').get(pk=pk)
                print(f"Found service record: {service_record}")
            except CarServiceRecord.DoesNotExist:
                print(f"CarServiceRecord with pk={pk} does not exist")
                return Response({
                    'error': f'Car service record with id {pk} not found'
                }, status=404)
            
            service_id = request.data.get('service_id')
            remarks = request.data.get('remarks', '')
            
            if not service_id:
                return Response({'error': 'service_id is required'}, status=400)
            
            try:
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                return Response({'error': 'Service not found'}, status=404)
            
            service_entry = ServiceEntry.objects.create(
                service_record=service_record,
                service=service,
                remarks=remarks,
                created_by=request.user
            )
            
            serializer = ServiceEntrySerializer(service_entry)
            return Response(serializer.data, status=201)
            
        except Exception as e:
            print(f"Unexpected error in add_service: {str(e)}")
            return Response({
                'error': f'An unexpected error occurred: {str(e)}'
            }, status=500)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='car_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by car ID'
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all car service records with optional car filtering"""
        car_id = request.query_params.get('car_id')
        if car_id:
            self.queryset = self.queryset.filter(car_id=car_id)
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
    methods=['delete'],
    parameters=[
        OpenApiParameter(
            name='entry_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='ID of the service entry to delete'
        )
    ],
    responses={204: None}
)
    @action(detail=True, methods=['delete'])
    def delete_service(self, request, pk=None):
        """Delete a service entry from an existing car service record"""
        service_record = self.get_object()
        entry_id = request.query_params.get('entry_id')

        if not entry_id:
            return Response({'error': 'entry_id is required'}, status=400)

        try:
            service_entry = service_record.service_entries.get(id=entry_id)
        except ServiceEntry.DoesNotExist:
            return Response({'error': 'ServiceEntry not found'}, status=404)

        service_entry.delete()
        return Response(status=204)
    
    

@extend_schema(tags=["Inventory Usage"])
class InventoryUsageViewSet(StandardizedModelViewSet):
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
    
    def perform_update(self, serializer):
    # Get the existing record before updating
        instance = self.get_object()
        old_quantity_used = instance.quantity_used

        # Save the updated instance
        updated_instance = serializer.save()

        # Compute the difference
        new_quantity_used = updated_instance.quantity_used
        diff = old_quantity_used - new_quantity_used  # positive if we're reducing usage

        # Update the stock
        product = updated_instance.product
        new_stock = product.quantity_in_stock + diff

        if new_stock < 0:
            raise serializers.ValidationError("Stock cannot go below zero!")

        product.quantity_in_stock = new_stock
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

        summary = queryset.values('product__name','product__quantity_in_stock').annotate(total_used=Sum('quantity_used')).order_by('-total_used')
        readable_summary = [
        {
            "Product Name": item["product__name"],
            "Remaining Stock": item["product__quantity_in_stock"],
            "Total Used till now": item["total_used"],
        }
        for item in summary
        ]
        return Response({
            "status_code": 200,
            "message": "Usage summary generated",
            "description": "Summary of inventory usage by product",
            "data": list(readable_summary)
        })