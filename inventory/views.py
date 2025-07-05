from rest_framework import viewsets, filters, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import InventoryItem, Supplier, ProductCategory
from .serializers import InventoryItemSerializer, SupplierSerializer, ProductCategorySerializer
from common.viewsets import StandardizedModelViewSet

class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            hasattr(request.user, 'role') and request.user.role.name.lower() in ['admin', 'staff']
        )

@extend_schema(tags=["Inventory"])
class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().select_related('supplier', 'category')
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'category__name', 'supplier__name']
    ordering_fields = ['name', 'quantity_in_stock', 'standard_rate', 'updated_at']
    ordering = ['name']

    @extend_schema(
        parameters=[
            OpenApiParameter(name='search', description='Search by name, SKU, supplier, category', required=False),
            OpenApiParameter(name='ordering', description='Order by name, quantity_in_stock, standard_rate', required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


from common.viewsets import StandardizedModelViewSet

@extend_schema(tags=["Supplier"])
class SupplierViewSet(StandardizedModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_person', 'phone_number', 'email']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    @extend_schema(
        parameters=[
            OpenApiParameter(name='search', description='Search by name, contact_person, phone, email', required=False),
            OpenApiParameter(name='ordering', description='Order by name, created_at, updated_at', required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
@extend_schema(tags=["Product Category"])
class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']