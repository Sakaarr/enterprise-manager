# purchases/filters.py
import django_filters
from django.db.models import Q, F
from .models import PurchaseOrder, PurchaseReceipt, PurchasePayment, PurchaseReturn


class PurchaseOrderFilter(django_filters.FilterSet):
    """
    Filter for Purchase Orders with comprehensive filtering options.
    """
    status = django_filters.ChoiceFilter(
        choices=PurchaseOrder.STATUS_CHOICES,
        help_text="Filter by purchase order status"
    )
    payment_status = django_filters.ChoiceFilter(
        choices=PurchaseOrder.PAYMENT_STATUS_CHOICES,
        help_text="Filter by payment status"
    )
    supplier = django_filters.NumberFilter(
        field_name='supplier__id',
        help_text="Filter by supplier ID"
    )
    supplier_name = django_filters.CharFilter(
        field_name='supplier__name',
        lookup_expr='icontains',
        help_text="Filter by supplier name (case insensitive)"
    )
    date_from = django_filters.DateFilter(
        field_name='order_date',
        lookup_expr='gte',
        help_text="Filter orders from date (YYYY-MM-DD)"
    )
    date_to = django_filters.DateFilter(
        field_name='order_date',
        lookup_expr='lte',
        help_text="Filter orders to date (YYYY-MM-DD)"
    )
    amount_min = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='gte',
        help_text="Minimum total amount"
    )
    amount_max = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='lte',
        help_text="Maximum total amount"
    )
    created_by = django_filters.NumberFilter(
        field_name='created_by__id',
        help_text="Filter by creator user ID"
    )
    has_pending_items = django_filters.BooleanFilter(
        method='filter_pending_items',
        help_text="Filter orders with pending items"
    )
    overdue = django_filters.BooleanFilter(
        method='filter_overdue',
        help_text="Filter overdue orders (past expected delivery date)"
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            'status', 'payment_status', 'supplier', 'supplier_name',
            'date_from', 'date_to', 'amount_min', 'amount_max',
            'created_by', 'has_pending_items', 'overdue'
        ]

    def filter_pending_items(self, queryset, name, value):
        """Filter orders that have pending items to receive."""
        if value:
            return queryset.filter(
                items__quantity__gt=F('items__received_quantity')
            ).distinct()
        return queryset

    def filter_overdue(self, queryset, name, value):
        """Filter orders that are overdue (past expected delivery date)."""
        if value:
            from django.utils import timezone
            today = timezone.now().date()
            return queryset.filter(
                expected_delivery_date__lt=today,
                status__in=['sent', 'confirmed', 'partial']
            )
        return queryset


class PurchaseReceiptFilter(django_filters.FilterSet):
    """
    Filter for Purchase Receipts.
    """
    status = django_filters.ChoiceFilter(
        choices=PurchaseReceipt.RECEIPT_STATUS_CHOICES,
        help_text="Filter by receipt status"
    )
    purchase_order = django_filters.NumberFilter(
        field_name='purchase_order__id',
        help_text="Filter by purchase order ID"
    )
    purchase_order_number = django_filters.CharFilter(
        field_name='purchase_order__po_number',
        lookup_expr='icontains',
        help_text="Filter by purchase order number"
    )
    supplier = django_filters.NumberFilter(
        field_name='purchase_order__supplier__id',
        help_text="Filter by supplier ID"
    )
    supplier_name = django_filters.CharFilter(
        field_name='purchase_order__supplier__name',
        lookup_expr='icontains',
        help_text="Filter by supplier name"
    )
    date_from = django_filters.DateFilter(
        field_name='receipt_date',
        lookup_expr='gte',
        help_text="Filter receipts from date (YYYY-MM-DD)"
    )
    date_to = django_filters.DateFilter(
        field_name='receipt_date',
        lookup_expr='lte',
        help_text="Filter receipts to date (YYYY-MM-DD)"
    )
    received_by = django_filters.NumberFilter(
        field_name='received_by__id',
        help_text="Filter by receiver user ID"
    )
    has_rejections = django_filters.BooleanFilter(
        method='filter_rejections',
        help_text="Filter receipts with rejected items"
    )

    class Meta:
        model = PurchaseReceipt
        fields = [
            'status', 'purchase_order', 'purchase_order_number',
            'supplier', 'supplier_name', 'date_from', 'date_to',
            'received_by', 'has_rejections'
        ]

    def filter_rejections(self, queryset, name, value):
        """Filter receipts that have rejected items."""
        if value:
            return queryset.filter(
                items__status__in=['rejected', 'damaged']
            ).distinct()
        return queryset


class PurchasePaymentFilter(django_filters.FilterSet):
    """
    Filter for Purchase Payments.
    """
    purchase_order = django_filters.NumberFilter(
        field_name='purchase_order__id',
        help_text="Filter by purchase order ID"
    )
    purchase_order_number = django_filters.CharFilter(
        field_name='purchase_order__po_number',
        lookup_expr='icontains',
        help_text="Filter by purchase order number"
    )
    supplier = django_filters.NumberFilter(
        field_name='purchase_order__supplier__id',
        help_text="Filter by supplier ID"
    )
    supplier_name = django_filters.CharFilter(
        field_name='purchase_order__supplier__name',
        lookup_expr='icontains',
        help_text="Filter by supplier name"
    )
    payment_method = django_filters.ChoiceFilter(
        choices=PurchasePayment.PAYMENT_METHOD_CHOICES,
        help_text="Filter by payment method"
    )
    date_from = django_filters.DateFilter(
        field_name='payment_date',
        lookup_expr='gte',
        help_text="Filter payments from date (YYYY-MM-DD)"
    )
    date_to = django_filters.DateFilter(
        field_name='payment_date',
        lookup_expr='lte',
        help_text="Filter payments to date (YYYY-MM-DD)"
    )
    amount_min = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte',
        help_text="Minimum payment amount"
    )
    amount_max = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        help_text="Maximum payment amount"
    )
    paid_by = django_filters.NumberFilter(
        field_name='paid_by__id',
        help_text="Filter by payer user ID"
    )

    class Meta:
        model = PurchasePayment
        fields = [
            'purchase_order', 'purchase_order_number', 'supplier',
            'supplier_name', 'payment_method', 'date_from', 'date_to',
            'amount_min', 'amount_max', 'paid_by'
        ]


class PurchaseReturnFilter(django_filters.FilterSet):
    """
    Filter for Purchase Returns.
    """
    status = django_filters.ChoiceFilter(
        choices=PurchaseReturn.RETURN_STATUS_CHOICES,
        help_text="Filter by return status"
    )
    purchase_order = django_filters.NumberFilter(
        field_name='purchase_order__id',
        help_text="Filter by purchase order ID"
    )
    purchase_order_number = django_filters.CharFilter(
        field_name='purchase_order__po_number',
        lookup_expr='icontains',
        help_text="Filter by purchase order number"
    )
    supplier = django_filters.NumberFilter(
        field_name='purchase_order__supplier__id',
        help_text="Filter by supplier ID"
    )
    supplier_name = django_filters.CharFilter(
        field_name='purchase_order__supplier__name',
        lookup_expr='icontains',
        help_text="Filter by supplier name"
    )
    date_from = django_filters.DateFilter(
        field_name='return_date',
        lookup_expr='gte',
        help_text="Filter returns from date (YYYY-MM-DD)"
    )
    date_to = django_filters.DateFilter(
        field_name='return_date',
        lookup_expr='lte',
        help_text="Filter returns to date (YYYY-MM-DD)"
    )
    amount_min = django_filters.NumberFilter(
        field_name='total_return_amount',
        lookup_expr='gte',
        help_text="Minimum return amount"
    )
    amount_max = django_filters.NumberFilter(
        field_name='total_return_amount',
        lookup_expr='lte',
        help_text="Maximum return amount"
    )
    requested_by = django_filters.NumberFilter(
        field_name='requested_by__id',
        help_text="Filter by requester user ID"
    )
    approved_by = django_filters.NumberFilter(
        field_name='approved_by__id',
        help_text="Filter by approver user ID"
    )
    pending_approval = django_filters.BooleanFilter(
        method='filter_pending_approval',
        help_text="Filter returns pending approval"
    )

    class Meta:
        model = PurchaseReturn
        fields = [
            'status', 'purchase_order', 'purchase_order_number',
            'supplier', 'supplier_name', 'date_from', 'date_to',
            'amount_min', 'amount_max', 'requested_by', 'approved_by',
            'pending_approval'
        ]

    def filter_pending_approval(self, queryset, name, value):
        """Filter returns that are pending approval."""
        if value:
            return queryset.filter(status='pending')
        return queryset