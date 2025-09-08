# purchases/utils.py
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import PurchaseOrder, PurchasePayment, PurchaseReturn


def generate_po_number(order_date=None):
    """
    Generate a new Purchase Order number.
    Format: PO{YEAR}-{6-digit-sequential-number}
    """
    if not order_date:
        order_date = timezone.now().date()
    
    year = order_date.year
    prefix = f"PO{year}"
    
    # Get last PO number for the year
    last_po = PurchaseOrder.objects.filter(
        po_number__startswith=prefix
    ).order_by('-po_number').first()
    
    if last_po:
        try:
            last_number = int(last_po.po_number.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    return f"{prefix}-{new_number:06d}"


def generate_receipt_number(receipt_date=None):
    """
    Generate a new Purchase Receipt number.
    Format: RCP{YEAR}-{6-digit-sequential-number}
    """
    if not receipt_date:
        receipt_date = timezone.now().date()
    
    from .models import PurchaseReceipt
    
    year = receipt_date.year
    prefix = f"RCP{year}"
    
    # Get last receipt number for the year
    last_receipt = PurchaseReceipt.objects.filter(
        receipt_number__startswith=prefix
    ).order_by('-receipt_number').first()
    
    if last_receipt:
        try:
            last_number = int(last_receipt.receipt_number.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    return f"{prefix}-{new_number:06d}"


def generate_return_number(return_date=None):
    """
    Generate a new Purchase Return number.
    Format: RTN{YEAR}-{6-digit-sequential-number}
    """
    if not return_date:
        return_date = timezone.now().date()
    
    year = return_date.year
    prefix = f"RTN{year}"
    
    # Get last return number for the year
    last_return = PurchaseReturn.objects.filter(
        return_number__startswith=prefix
    ).order_by('-return_number').first()
    
    if last_return:
        try:
            last_number = int(last_return.return_number.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    return f"{prefix}-{new_number:06d}"


def calculate_purchase_order_totals(purchase_order):
    """
    Calculate and update purchase order totals.
    """
    # Calculate subtotal from items
    subtotal = purchase_order.items.aggregate(
        total=Sum(F('quantity') * F('unit_price'))
    )['total'] or Decimal('0.00')
    
    # Calculate total amount
    total_amount = subtotal + purchase_order.tax_amount - purchase_order.discount_amount
    
    # Update the purchase order
    purchase_order.subtotal = subtotal
    purchase_order.total_amount = total_amount
    purchase_order.save(update_fields=['subtotal', 'total_amount'])
    
    return {
        'subtotal': subtotal,
        'total_amount': total_amount
    }


def update_purchase_order_payment_status(purchase_order):
    """
    Update purchase order payment status based on payments made.
    """
    total_paid = purchase_order.payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    if total_paid >= purchase_order.total_amount:
        purchase_order.payment_status = 'paid'
    elif total_paid > 0:
        purchase_order.payment_status = 'partial'
    else:
        purchase_order.payment_status = 'pending'
    
    purchase_order.save(update_fields=['payment_status'])
    return purchase_order.payment_status


def update_purchase_order_status(purchase_order):
    """
    Update purchase order status based on receipt status.
    """
    total_ordered = purchase_order.items.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    total_received = purchase_order.items.aggregate(
        total=Sum('received_quantity')
    )['total'] or 0
    
    if total_received == 0:
        # No items received yet
        if purchase_order.status == 'draft':
            pass  # Keep as draft
        elif purchase_order.status not in ['sent', 'confirmed']:
            pass  # Keep current status
    elif total_received >= total_ordered:
        # All items received
        purchase_order.status = 'completed'
    else:
        # Partially received
        purchase_order.status = 'partial'
    
    purchase_order.save(update_fields=['status'])
    return purchase_order.status


def get_purchase_analytics(date_from=None, date_to=None):
    """
    Get comprehensive purchase analytics for a date range.
    """
    queryset = PurchaseOrder.objects.all()
    
    if date_from:
        queryset = queryset.filter(order_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(order_date__lte=date_to)
    
    # Basic statistics
    total_orders = queryset.count()
    
    order_stats = queryset.aggregate(
        total_amount=Sum('total_amount'),
        avg_order_value=Sum('total_amount') / Count('id') if total_orders > 0 else 0
    )
    
    # Status breakdown
    status_breakdown = queryset.values('status').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('status')
    
    # Payment statistics
    payment_stats = queryset.aggregate(
        pending_orders=Count('id', filter=Q(payment_status='pending')),
        partial_paid_orders=Count('id', filter=Q(payment_status='partial')),
        fully_paid_orders=Count('id', filter=Q(payment_status='paid'))
    )
    
    # Calculate total payments made
    total_payments = PurchasePayment.objects.filter(
        purchase_order__in=queryset
    ).aggregate(Sum('amount'))['amount'] or Decimal('0.00')
    
    # Outstanding amount
    total_order_amount = order_stats['total_amount'] or Decimal('0.00')
    outstanding_amount = total_order_amount - total_payments
    
    # Return statistics
    return_stats = PurchaseReturn.objects.filter(
        purchase_order__in=queryset
    ).aggregate(
        total_returns=Count('id'),
        total_return_amount=Sum('total_return_amount')
    )
    
    return {
        'summary': {
            'total_orders': total_orders,
            'total_amount': total_order_amount,
            'average_order_value': order_stats['avg_order_value'] or Decimal('0.00'),
            'total_payments': total_payments,
            'outstanding_amount': outstanding_amount,
        },
        'status_breakdown': list(status_breakdown),
        'payment_breakdown': payment_stats,
        'returns': {
            'total_returns': return_stats['total_returns'] or 0,
            'total_return_amount': return_stats['total_return_amount'] or Decimal('0.00')
        }
    }


def get_supplier_performance(supplier_id=None, date_from=None, date_to=None):
    """
    Get supplier performance metrics.
    """
    queryset = PurchaseOrder.objects.all()
    
    if supplier_id:
        queryset = queryset.filter(supplier_id=supplier_id)
    if date_from:
        queryset = queryset.filter(order_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(order_date__lte=date_to)
    
    supplier_stats = queryset.values(
        'supplier_id', 'supplier__name'
    ).annotate(
        total_orders=Count('id'),
        total_amount=Sum('total_amount'),
        avg_order_value=Sum('total_amount') / Count('id'),
        on_time_delivery_count=Count(
            'id',
            filter=Q(
                receipts__receipt_date__lte=F('expected_delivery_date'),
                status='completed'
            )
        ),
        total_completed_orders=Count('id', filter=Q(status='completed')),
        return_orders=Count('returns', distinct=True),
        return_amount=Sum('returns__total_return_amount')
    ).order_by('-total_amount')
    
    # Calculate on-time delivery percentage
    for stat in supplier_stats:
        completed_orders = stat['total_completed_orders']
        if completed_orders > 0:
            stat['on_time_delivery_rate'] = (
                stat['on_time_delivery_count'] / completed_orders
            ) * 100
        else:
            stat['on_time_delivery_rate'] = 0
        
        # Calculate return rate
        if stat['total_orders'] > 0:
            stat['return_rate'] = (stat['return_orders'] / stat['total_orders']) * 100
        else:
            stat['return_rate'] = 0
    
    return list(supplier_stats)


def get_overdue_orders():
    """
    Get purchase orders that are overdue.
    """
    today = timezone.now().date()
    
    overdue_orders = PurchaseOrder.objects.filter(
        expected_delivery_date__lt=today,
        status__in=['sent', 'confirmed', 'partial']
    ).select_related('supplier').prefetch_related('items')
    
    overdue_data = []
    for order in overdue_orders:
        days_overdue = (today - order.expected_delivery_date).days
        pending_items = order.items.aggregate(
            pending=Sum(F('quantity') - F('received_quantity'))
        )['pending'] or 0
        
        overdue_data.append({
            'purchase_order': order,
            'days_overdue': days_overdue,
            'pending_items': pending_items,
            'total_amount': order.total_amount
        })
    
    return overdue_data


def validate_purchase_order_transition(from_status, to_status):
    """
    Validate if status transition is allowed.
    """
    valid_transitions = {
        'draft': ['sent', 'cancelled'],
        'sent': ['confirmed', 'cancelled'],
        'confirmed': ['partial', 'completed'],
        'partial': ['completed'],
        'completed': [],  # No transitions from completed
        'cancelled': []   # No transitions from cancelled
    }
    
    return to_status in valid_transitions.get(from_status, [])


def get_purchase_notifications():
    """
    Get purchase-related notifications.
    """
    today = timezone.now().date()
    notifications = []
    
    # Overdue orders
    overdue_count = PurchaseOrder.objects.filter(
        expected_delivery_date__lt=today,
        status__in=['sent', 'confirmed', 'partial']
    ).count()
    
    if overdue_count > 0:
        notifications.append({
            'type': 'overdue_orders',
            'message': f'{overdue_count} purchase order(s) are overdue',
            'count': overdue_count,
            'priority': 'high'
        })
    
    # Pending receipts
    pending_receipts = PurchaseOrder.objects.filter(
        status__in=['confirmed', 'partial']
    ).count()
    
    if pending_receipts > 0:
        notifications.append({
            'type': 'pending_receipts',
            'message': f'{pending_receipts} purchase order(s) are awaiting receipt',
            'count': pending_receipts,
            'priority': 'medium'
        })
    
    # Pending return approvals
    pending_returns = PurchaseReturn.objects.filter(status='pending').count()
    
    if pending_returns > 0:
        notifications.append({
            'type': 'pending_returns',
            'message': f'{pending_returns} purchase return(s) are pending approval',
            'count': pending_returns,
            'priority': 'medium'
        })
    
    return notifications