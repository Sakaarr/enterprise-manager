# purchases/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend    
from django.db.models import Sum, Count, Q
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
)
from drf_spectacular.types import OpenApiTypes

from .models import (
    PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptItem,
    PurchasePayment, PurchaseReturn, PurchaseReturnItem
)
from .serializers import (
    PurchaseOrderListSerializer, PurchaseOrderDetailSerializer, 
    PurchaseOrderCreateSerializer, PurchaseOrderItemSerializer,
    PurchaseReceiptListSerializer, PurchaseReceiptDetailSerializer,
    PurchaseReceiptCreateSerializer, PurchaseReceiptItemSerializer,
    PurchasePaymentSerializer, PurchaseReturnListSerializer,
    PurchaseReturnDetailSerializer, PurchaseReturnCreateSerializer,
    PurchaseReturnItemSerializer, PurchaseAnalyticsSerializer,
    SupplierPurchaseStatsSerializer, MonthlyPurchaseTrendSerializer
)
from .filters import (
    PurchaseOrderFilter, PurchaseReceiptFilter, PurchasePaymentFilter,
    PurchaseReturnFilter
)
# from core.permissions import IsOwnerOrReadOnly
# from core.pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        summary="List purchase orders",
        description="Retrieve a paginated list of purchase orders with filtering and search capabilities.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status (draft, sent, confirmed, partial, completed, cancelled)'
            ),
            OpenApiParameter(
                name='payment_status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by payment status (pending, partial, paid)'
            ),
            OpenApiParameter(
                name='supplier',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by supplier ID'
            ),
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter orders from date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter orders to date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in PO number, supplier name, or notes'
            ),
        ],
        responses={200: PurchaseOrderListSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Get purchase order details",
        description="Retrieve detailed information about a specific purchase order including all items.",
        responses={
            200: PurchaseOrderDetailSerializer,
            404: OpenApiResponse(description="Purchase order not found")
        }
    ),
    create=extend_schema(
        summary="Create new purchase order",
        description="Create a new purchase order with items. The PO number will be auto-generated.",
        request=PurchaseOrderCreateSerializer,
        responses={
            201: PurchaseOrderDetailSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    ),
    update=extend_schema(
        summary="Update purchase order",
        description="Update a purchase order and its items. Only draft orders can be fully updated.",
        request=PurchaseOrderCreateSerializer,
        responses={
            200: PurchaseOrderDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Purchase order not found")
        }
    ),
    partial_update=extend_schema(
        summary="Partially update purchase order",
        description="Partially update purchase order fields. Status changes have restrictions.",
        responses={
            200: PurchaseOrderDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Purchase order not found")
        }
    ),
    destroy=extend_schema(
        summary="Delete purchase order",
        description="Delete a purchase order. Only draft orders can be deleted.",
        responses={
            204: OpenApiResponse(description="Purchase order deleted"),
            400: OpenApiResponse(description="Cannot delete non-draft order"),
            404: OpenApiResponse(description="Purchase order not found")
        }
    )
)
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing purchase orders.
    
    Provides CRUD operations for purchase orders with the following features:
    - Auto-generation of PO numbers
    - Status-based workflow management
    - Filtering by status, payment status, supplier, and date range
    - Search functionality across PO number, supplier name, and notes
    - Bulk operations for status updates
    """
    queryset = PurchaseOrder.objects.select_related(
        'supplier', 'created_by'
    ).prefetch_related('items__inventory_item')
    permission_classes = [IsAuthenticated]
    # pagination_class = StandardResultsSetPagination
    filterset_class = PurchaseOrderFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['po_number', 'supplier__name', 'notes']
    ordering_fields = ['order_date', 'total_amount', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseOrderListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PurchaseOrderCreateSerializer
        return PurchaseOrderDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        if instance.status != 'draft':
            raise ValidationError("Only draft purchase orders can be deleted.")
        instance.delete()

    @extend_schema(
        summary="Send purchase order to supplier",
        description="Change purchase order status from draft to sent.",
        request=None,
        responses={
            200: OpenApiResponse(description="Purchase order sent successfully"),
            400: OpenApiResponse(description="Invalid status transition")
        }
    )
    @action(detail=True, methods=['post'])
    def send_to_supplier(self, request, pk=None):
        """Send purchase order to supplier (draft -> sent)."""
        purchase_order = self.get_object()
        
        if purchase_order.status != 'draft':
            return Response(
                {"error": "Only draft purchase orders can be sent to supplier."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase_order.status = 'sent'
        purchase_order.save()
        
        serializer = self.get_serializer(purchase_order)
        return Response({
            "message": "Purchase order sent to supplier successfully.",
            "data": serializer.data
        })

    @extend_schema(
        summary="Confirm purchase order",
        description="Confirm purchase order from supplier (sent -> confirmed).",
        request=None,
        responses={
            200: OpenApiResponse(description="Purchase order confirmed successfully"),
            400: OpenApiResponse(description="Invalid status transition")
        }
    )
    @action(detail=True, methods=['post'])
    def confirm_order(self, request, pk=None):
        """Confirm purchase order from supplier (sent -> confirmed)."""
        purchase_order = self.get_object()
        
        if purchase_order.status != 'sent':
            return Response(
                {"error": "Only sent purchase orders can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase_order.status = 'confirmed'
        purchase_order.save()
        
        serializer = self.get_serializer(purchase_order)
        return Response({
            "message": "Purchase order confirmed successfully.",
            "data": serializer.data
        })

    @extend_schema(
        summary="Cancel purchase order",
        description="Cancel a purchase order. Only draft or sent orders can be cancelled.",
        request=None,
        responses={
            200: OpenApiResponse(description="Purchase order cancelled successfully"),
            400: OpenApiResponse(description="Cannot cancel order in current status")
        }
    )
    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        """Cancel purchase order."""
        purchase_order = self.get_object()
        
        if purchase_order.status not in ['draft', 'sent']:
            return Response(
                {"error": "Only draft or sent purchase orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase_order.status = 'cancelled'
        purchase_order.save()
        
        serializer = self.get_serializer(purchase_order)
        return Response({
            "message": "Purchase order cancelled successfully.",
            "data": serializer.data
        })

    @extend_schema(
        summary="Get purchase order summary",
        description="Get summary statistics for a purchase order including payment and receipt status.",
        responses={200: OpenApiResponse(description="Purchase order summary")}
    )
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get purchase order summary with payment and receipt details."""
        purchase_order = self.get_object()
        
        # Calculate payment summary
        total_paid = purchase_order.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        pending_amount = purchase_order.total_amount - total_paid
        
        # Calculate receipt summary
        total_received_items = purchase_order.items.aggregate(
            total=Sum('received_quantity')
        )['total'] or 0
        
        total_ordered_items = purchase_order.items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        # Get latest receipt
        latest_receipt = purchase_order.receipts.first()
        
        summary_data = {
            'purchase_order': PurchaseOrderDetailSerializer(purchase_order).data,
            'payment_summary': {
                'total_amount': purchase_order.total_amount,
                'total_paid': total_paid,
                'pending_amount': pending_amount,
                'payment_status': purchase_order.payment_status,
                'total_payments': purchase_order.payments.count()
            },
            'receipt_summary': {
                'total_ordered_items': total_ordered_items,
                'total_received_items': total_received_items,
                'pending_items': total_ordered_items - total_received_items,
                'receipt_status': purchase_order.status,
                'total_receipts': purchase_order.receipts.count(),
                'latest_receipt_date': latest_receipt.receipt_date if latest_receipt else None
            }
        }
        
        return Response(summary_data)


@extend_schema_view(
    list=extend_schema(
        summary="List purchase receipts",
        description="Retrieve a paginated list of purchase receipts with filtering capabilities.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status (received, quality_check, accepted, rejected, partial_accepted)'
            ),
            OpenApiParameter(
                name='purchase_order',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by purchase order ID'
            ),
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter receipts from date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter receipts to date (YYYY-MM-DD)'
            ),
        ],
        responses={200: PurchaseReceiptListSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Get purchase receipt details",
        description="Retrieve detailed information about a specific purchase receipt including all items.",
        responses={
            200: PurchaseReceiptDetailSerializer,
            404: OpenApiResponse(description="Purchase receipt not found")
        }
    ),
    create=extend_schema(
        summary="Create new purchase receipt",
        description="Create a new purchase receipt for items received against a purchase order.",
        request=PurchaseReceiptCreateSerializer,
        responses={
            201: PurchaseReceiptDetailSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    ),
    update=extend_schema(
        summary="Update purchase receipt",
        description="Update a purchase receipt and its items.",
        request=PurchaseReceiptCreateSerializer,
        responses={
            200: PurchaseReceiptDetailSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
)
class PurchaseReceiptViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing purchase receipts.
    
    Handles the receipt of goods against purchase orders including:
    - Recording received quantities
    - Quality check processes
    - Acceptance/rejection of items
    - Automatic inventory updates on acceptance
    """
    queryset = PurchaseReceipt.objects.select_related(
        'purchase_order__supplier', 'received_by'
    ).prefetch_related('items__purchase_order_item__inventory_item')
    permission_classes = [IsAuthenticated]
    # pagination_class = StandardResultsSetPagination
    filterset_class = PurchaseReceiptFilter
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['receipt_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseReceiptListSerializer
        elif self.action in ['create', 'update']:
            return PurchaseReceiptCreateSerializer
        return PurchaseReceiptDetailSerializer

    @extend_schema(
        summary="Accept receipt items",
        description="Accept all or specific items in a purchase receipt and update inventory.",
        request=OpenApiParameter(
            name='item_ids',
            type=OpenApiTypes.OBJECT,
            description='List of receipt item IDs to accept'
        ),
        responses={
            200: OpenApiResponse(description="Items accepted successfully"),
            400: OpenApiResponse(description="Invalid items or status")
        }
    )
    @action(detail=True, methods=['post'])
    def accept_items(self, request, pk=None):
        """Accept receipt items and update inventory."""
        receipt = self.get_object()
        item_ids = request.data.get('item_ids', [])
        
        with transaction.atomic():
            if item_ids:
                items = receipt.items.filter(id__in=item_ids, status='received')
            else:
                items = receipt.items.filter(status='received')
            
            if not items.exists():
                return Response(
                    {"error": "No valid items found to accept."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            accepted_count = 0
            for item in items:
                item.status = 'accepted'
                item.accepted_quantity = item.received_quantity
                item.save()
                accepted_count += 1
            
            # Update receipt status
            if receipt.items.filter(status='received').count() == 0:
                if receipt.items.filter(status='rejected').exists():
                    receipt.status = 'partial_accepted'
                else:
                    receipt.status = 'accepted'
                receipt.save()
        
        return Response({
            "message": f"{accepted_count} items accepted successfully.",
            "data": PurchaseReceiptDetailSerializer(receipt).data
        })

    @extend_schema(
        summary="Reject receipt items",
        description="Reject specific items in a purchase receipt with rejection reason.",
        request=OpenApiParameter(
            name='rejections',
            type=OpenApiTypes.OBJECT,
            description='List of items with rejection details'
        ),
        responses={
            200: OpenApiResponse(description="Items rejected successfully"),
            400: OpenApiResponse(description="Invalid items or data")
        }
    )
    @action(detail=True, methods=['post'])
    def reject_items(self, request, pk=None):
        """Reject receipt items with reasons."""
        receipt = self.get_object()
        rejections = request.data.get('rejections', [])
        
        if not rejections:
            return Response(
                {"error": "No rejection data provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            rejected_count = 0
            for rejection in rejections:
                item_id = rejection.get('item_id')
                rejected_qty = rejection.get('rejected_quantity', 0)
                reason = rejection.get('reason', '')
                
                try:
                    item = receipt.items.get(id=item_id, status='received')
                    if rejected_qty > item.received_quantity:
                        continue
                    
                    item.rejected_quantity = rejected_qty
                    item.accepted_quantity = item.received_quantity - rejected_qty
                    item.rejection_reason = reason
                    item.status = 'rejected' if rejected_qty == item.received_quantity else 'partial_accepted'
                    item.save()
                    rejected_count += 1
                    
                except PurchaseReceiptItem.DoesNotExist:
                    continue
            
            # Update receipt status
            if receipt.items.filter(status='received').count() == 0:
                if receipt.items.filter(status__in=['rejected', 'partial_accepted']).exists():
                    receipt.status = 'partial_accepted'
                receipt.save()
        
        return Response({
            "message": f"{rejected_count} items processed successfully.",
            "data": PurchaseReceiptDetailSerializer(receipt).data
        })


@extend_schema_view(
    list=extend_schema(
        summary="List purchase payments",
        description="Retrieve a paginated list of purchase payments with filtering capabilities.",
        parameters=[
            OpenApiParameter(
                name='purchase_order',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by purchase order ID'
            ),
            OpenApiParameter(
                name='payment_method',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by payment method'
            ),
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter payments from date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter payments to date (YYYY-MM-DD)'
            ),
        ],
        responses={200: PurchasePaymentSerializer(many=True)}
    ),
    create=extend_schema(
        summary="Record new payment",
        description="Record a new payment against a purchase order.",
        request=PurchasePaymentSerializer,
        responses={
            201: PurchasePaymentSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
)
class PurchasePaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing purchase payments.
    
    Handles payment recording against purchase orders with:
    - Automatic payment status updates
    - Payment method tracking
    - Reference number management
    """
    queryset = PurchasePayment.objects.select_related(
        'purchase_order__supplier', 'paid_by'
    )
    serializer_class = PurchasePaymentSerializer
    permission_classes = [IsAuthenticated]
    # pagination_class = StandardResultsSetPagination
    filterset_class = PurchasePaymentFilter
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']  # No updates or deletes


@extend_schema_view(
    list=extend_schema(
        summary="List purchase returns",
        description="Retrieve a paginated list of purchase returns with filtering capabilities.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status (pending, approved, processed, rejected)'
            ),
            OpenApiParameter(
                name='purchase_order',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by purchase order ID'
            ),
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter returns from date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter returns to date (YYYY-MM-DD)'
            ),
        ],
        responses={200: PurchaseReturnListSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Get purchase return details",
        description="Retrieve detailed information about a specific purchase return including all items.",
        responses={
            200: PurchaseReturnDetailSerializer,
            404: OpenApiResponse(description="Purchase return not found")
        }
    ),
    create=extend_schema(
        summary="Create new purchase return",
        description="Create a new purchase return request with items to be returned.",
        request=PurchaseReturnCreateSerializer,
        responses={
            201: PurchaseReturnDetailSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
)
class PurchaseReturnViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing purchase returns.
    
    Handles the return of goods to suppliers including:
    - Return request creation
    - Approval workflow
    - Inventory adjustments on processing
    """
    queryset = PurchaseReturn.objects.select_related(
        'purchase_order__supplier', 'requested_by', 'approved_by'
    ).prefetch_related('items__inventory_item')
    permission_classes = [IsAuthenticated]
    # pagination_class = StandardResultsSetPagination
    filterset_class = PurchaseReturnFilter
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['return_date', 'total_return_amount', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseReturnListSerializer
        elif self.action == 'create':
            return PurchaseReturnCreateSerializer
        return PurchaseReturnDetailSerializer

    @extend_schema(
        summary="Approve purchase return",
        description="Approve a pending purchase return request.",
        request=None,
        responses={
            200: OpenApiResponse(description="Return approved successfully"),
            400: OpenApiResponse(description="Invalid status for approval")
        }
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a purchase return."""
        purchase_return = self.get_object()
        
        if purchase_return.status != 'pending':
            return Response(
                {"error": "Only pending returns can be approved."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase_return.status = 'approved'
        purchase_return.approved_by = request.user
        purchase_return.save()
        
        serializer = self.get_serializer(purchase_return)
        return Response({
            "message": "Purchase return approved successfully.",
            "data": serializer.data
        })

    @extend_schema(
        summary="Process purchase return",
        description="Process an approved purchase return and update inventory.",
        request=None,
        responses={
            200: OpenApiResponse(description="Return processed successfully"),
            400: OpenApiResponse(description="Invalid status for processing")
        }
    )
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a purchase return and update inventory."""
        purchase_return = self.get_object()
        
        if purchase_return.status != 'approved':
            return Response(
                {"error": "Only approved returns can be processed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            purchase_return.status = 'processed'
            purchase_return.save()
            
            # Update inventory for each return item
            for item in purchase_return.items.all():
                inventory_item = item.inventory_item
                if inventory_item.quantity_in_stock >= item.quantity:
                    inventory_item.quantity_in_stock -= item.quantity
                    inventory_item.save()
        
        serializer = self.get_serializer(purchase_return)
        return Response({
            "message": "Purchase return processed successfully.",
            "data": serializer.data
        })

    @extend_schema(
        summary="Reject purchase return",
        description="Reject a pending purchase return request.",
        request=None,
        responses={
            200: OpenApiResponse(description="Return rejected successfully"),
            400: OpenApiResponse(description="Invalid status for rejection")
        }
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a purchase return."""
        purchase_return = self.get_object()
        
        if purchase_return.status != 'pending':
            return Response(
                {"error": "Only pending returns can be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase_return.status = 'rejected'
        purchase_return.save()
        
        serializer = self.get_serializer(purchase_return)
        return Response({
            "message": "Purchase return rejected successfully.",
            "data": serializer.data
        })


@extend_schema_view(
    analytics=extend_schema(
        summary="Get purchase analytics",
        description="Retrieve comprehensive analytics for purchase operations.",
        parameters=[
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Analytics from date (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Analytics to date (YYYY-MM-DD)'
            ),
        ],
        responses={200: PurchaseAnalyticsSerializer}
    ),
    supplier_stats=extend_schema(
        summary="Get supplier purchase statistics",
        description="Retrieve purchase statistics grouped by supplier.",
        responses={200: SupplierPurchaseStatsSerializer(many=True)}
    ),
    monthly_trends=extend_schema(
        summary="Get monthly purchase trends",
        description="Retrieve monthly purchase trends for the last 12 months.",
        responses={200: MonthlyPurchaseTrendSerializer(many=True)}
    )
)
class PurchaseAnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for purchase analytics and reporting.
    
    Provides various analytical endpoints for purchase data including:
    - Overall purchase statistics
    - Supplier-wise performance
    - Monthly trends and patterns
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get comprehensive purchase analytics."""
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        queryset = PurchaseOrder.objects.all()
        
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        
        # Basic statistics
        total_orders = queryset.count()
        total_amount = queryset.aggregate(Sum('total_amount'))['total_amount'] or Decimal('0.00')
        pending_orders = queryset.filter(status__in=['draft', 'sent', 'confirmed', 'partial']).count()
        completed_orders = queryset.filter(status='completed').count()
        
        # Payment statistics
        total_payments = PurchasePayment.objects.filter(
            purchase_order__in=queryset
        ).aggregate(Sum('amount'))['amount'] or Decimal('0.00')
        
        outstanding_amount = total_amount - total_payments
        
        # Return statistics
        returns_queryset = PurchaseReturn.objects.filter(purchase_order__in=queryset)
        total_returns = returns_queryset.count()
        total_return_amount = returns_queryset.aggregate(
            Sum('total_return_amount')
        )['total_return_amount'] or Decimal('0.00')
        
        analytics_data = {
            'total_purchase_orders': total_orders,
            'total_purchase_amount': total_amount,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'total_payments_made': total_payments,
            'outstanding_amount': outstanding_amount,
            'total_returns': total_returns,
            'total_return_amount': total_return_amount
        }
        
        serializer = PurchaseAnalyticsSerializer(data=analytics_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def supplier_stats(self, request):
        """Get supplier-wise purchase statistics."""
        from django.db.models import Max
        
        supplier_stats = PurchaseOrder.objects.values(
            'supplier_id', 'supplier__name'
        ).annotate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount'),
            pending_amount=Sum(
                'total_amount',
                filter=Q(payment_status__in=['pending', 'partial'])
            ),
            last_order_date=Max('order_date')
        ).order_by('-total_amount')
        
        stats_data = []
        for stat in supplier_stats:
            stats_data.append({
                'supplier_id': stat['supplier_id'],
                'supplier_name': stat['supplier__name'],
                'total_orders': stat['total_orders'],
                'total_amount': stat['total_amount'] or Decimal('0.00'),
                'pending_amount': stat['pending_amount'] or Decimal('0.00'),
                'last_order_date': stat['last_order_date']
            })
        
        serializer = SupplierPurchaseStatsSerializer(data=stats_data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)