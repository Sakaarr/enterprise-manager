from rest_framework import serializers
from decimal import Decimal
from .models import Bill, PaidBill


class BillCalculationSerializer(serializers.Serializer):
    car_id = serializers.IntegerField(min_value=1, help_text="ID of the car to generate bill for")
    discount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        default=Decimal('0'),
        min_value=Decimal('0'),
        help_text="Discount amount to apply"
    )
    amount_paid = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        default=Decimal('0'),
        min_value=Decimal('0'),
        help_text="Amount already paid"
    )

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def validate_amount_paid(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount paid cannot be negative.")
        return value


class BillResponseSerializer(serializers.Serializer):
    """Enhanced serializer for bill calculation response"""
    bill_id = serializers.IntegerField(help_text="Generated bill ID")
    total_service_cost = serializers.CharField(help_text="Total cost of services")
    total_inventory_cost = serializers.CharField(help_text="Total cost of inventory/products")
    total_amount = serializers.CharField(help_text="Total bill amount before discount and payment")
    discount = serializers.CharField(help_text="Applied discount amount")
    amount_paid = serializers.CharField(help_text="Amount already paid")
    amount_remaining = serializers.CharField(help_text="Remaining amount to be paid")
    created_at = serializers.CharField(help_text="Bill creation timestamp")
    is_fully_paid = serializers.BooleanField(help_text="Whether the bill is fully paid", required=False)
    service_records_cleaned = serializers.BooleanField(
        help_text="Whether service records were cleaned up after full payment", 
        required=False
    )



class BillUpdateSerializer(serializers.Serializer):
    """Serializer for updating bill payment information"""
    
    discount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        min_value=Decimal('0'),
        help_text="New discount amount (will replace existing discount)"
    )
    additional_payment = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        min_value=Decimal('0'),
        default=Decimal('0'),
        help_text="Additional payment amount to add to existing payment"
    )

    def validate(self, attrs):
        if not attrs.get('discount') and not attrs.get('additional_payment'):
            raise serializers.ValidationError(
                "Either discount or additional_payment must be provided."
            )
        return attrs

    def validate_discount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def validate_additional_payment(self, value):
        if value < 0:
            raise serializers.ValidationError("Additional payment cannot be negative.")
        return value


class BillListSerializer(serializers.ModelSerializer):
    """Serializer for listing bills with related information"""
    
    car_info = serializers.SerializerMethodField()
    entered_by_name = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            'id', 'car_info', 'total_service_cost', 'total_inventory_cost',
            'total_amount', 'discount', 'amount_paid', 'amount_remaining',
            'created_at', 'entered_by_name', 'is_fully_paid', 'payment_status'
        ]

    def get_car_info(self, obj):
        return {
            'id': obj.car.id,
            'plate_number': obj.car.plate_number,
            # Add other car fields as needed
        }

    def get_entered_by_name(self, obj):
        if obj.entered_by:
            return f"{obj.entered_by.first_name} {obj.entered_by.last_name}".strip() or obj.entered_by.username
        return None

    def get_is_fully_paid(self, obj):
        return obj.amount_remaining <= 0

    def get_payment_status(self, obj):
        if obj.amount_remaining <= 0:
            return "Fully Paid"
        elif obj.amount_paid > 0:
            return "Partially Paid"
        else:
            return "Unpaid"


class PaidBillSerializer(serializers.ModelSerializer):
    car_plate_number = serializers.CharField(source='car.plate_number', read_only=True)

    class Meta:
        model = PaidBill
        fields = '__all__'
        
        
        
class DateRangeAnalyticsSerializer(serializers.Serializer):
    """Base serializer for date range analytics requests"""
    start_date = serializers.DateField(
        help_text="Start date for analytics period (YYYY-MM-DD format)",
        required=False
    )
    end_date = serializers.DateField(
        help_text="End date for analytics period (YYYY-MM-DD format)",
        required=False
    )
    group_by = serializers.ChoiceField(
        choices=['day', 'week', 'month', 'year'],
        default='day',
        help_text="Group results by time period"
    )

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        
        return attrs


class RevenueAnalyticsResponseSerializer(serializers.Serializer):
    """Serializer for revenue analytics response"""
    period = serializers.CharField(help_text="Time period (e.g., '2025-01-15' for day)")
    total_revenue = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Total revenue for the period"
    )
    service_revenue = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Revenue from services"
    )
    inventory_revenue = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Revenue from inventory/products"
    )
    bills_count = serializers.IntegerField(help_text="Number of bills in this period")
    average_bill_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Average bill amount for the period"
    )


class PaymentAnalyticsResponseSerializer(serializers.Serializer):
    """Serializer for payment analytics response"""
    period = serializers.CharField(help_text="Time period")
    total_payments = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total payments received"
    )
    fully_paid_bills = serializers.IntegerField(help_text="Number of fully paid bills")
    partially_paid_bills = serializers.IntegerField(help_text="Number of partially paid bills")
    unpaid_bills = serializers.IntegerField(help_text="Number of unpaid bills")
    outstanding_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total outstanding amount"
    )


class TopCustomersResponseSerializer(serializers.Serializer):
    """Serializer for top customers analytics"""
    car_id = serializers.IntegerField(help_text="Car ID")
    car_plate_number = serializers.CharField(help_text="Car plate number")
    total_bills = serializers.IntegerField(help_text="Total number of bills")
    total_revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue from this customer"
    )
    average_bill_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Average bill amount"
    )
    last_service_date = serializers.DateTimeField(
        help_text="Date of last service",
        allow_null=True
    )


class ServiceAnalyticsResponseSerializer(serializers.Serializer):
    """Serializer for service analytics response"""
    service_name = serializers.CharField(help_text="Name of the service")
    service_count = serializers.IntegerField(help_text="Number of times service was provided")
    total_revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue from this service"
    )
    average_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Average price of this service"
    )


class InventoryAnalyticsResponseSerializer(serializers.Serializer):
    """Serializer for inventory analytics response"""
    product_name = serializers.CharField(help_text="Name of the product")
    quantity_used = serializers.IntegerField(help_text="Total quantity used")
    total_revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue from this product"
    )
    average_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Average price per unit"
    )


class DashboardSummaryResponseSerializer(serializers.Serializer):
    """Serializer for dashboard summary analytics"""
    total_revenue_today = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue for today"
    )
    total_revenue_this_month = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue for current month"
    )
    total_bills_today = serializers.IntegerField(help_text="Number of bills created today")
    total_bills_this_month = serializers.IntegerField(help_text="Number of bills created this month")
    pending_payments = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total amount of pending payments"
    )
    pending_bills_count = serializers.IntegerField(help_text="Number of bills with pending payments")
    average_bill_amount_today = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Average bill amount for today"
    )
    top_service_today = serializers.CharField(
        help_text="Most popular service today",
        allow_null=True
    )


class MonthlyComparisonResponseSerializer(serializers.Serializer):
    """Serializer for monthly comparison analytics"""
    current_month = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=2),
        help_text="Current month statistics"
    )
    previous_month = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=2),
        help_text="Previous month statistics"
    )
    growth_percentage = serializers.DictField(
        child=serializers.DecimalField(max_digits=5, decimal_places=2),
        help_text="Growth percentage compared to previous month"
    )


class PaymentStatusSummarySerializer(serializers.Serializer):
    """Serializer for payment status summary"""
    total_bills = serializers.IntegerField(help_text="Total number of bills")
    fully_paid = serializers.IntegerField(help_text="Number of fully paid bills")
    partially_paid = serializers.IntegerField(help_text="Number of partially paid bills")
    unpaid = serializers.IntegerField(help_text="Number of unpaid bills")
    fully_paid_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of fully paid bills"
    )
    total_outstanding = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total outstanding amount"
    )


class PeakHoursAnalyticsSerializer(serializers.Serializer):
    """Serializer for peak hours analytics"""
    hour = serializers.IntegerField(help_text="Hour of the day (0-23)")
    bills_count = serializers.IntegerField(help_text="Number of bills created in this hour")
    total_revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue in this hour"
    )


class CustomerRetentionSerializer(serializers.Serializer):
    """Serializer for customer retention analytics"""
    period = serializers.CharField(help_text="Time period")
    new_customers = serializers.IntegerField(help_text="Number of new customers")
    returning_customers = serializers.IntegerField(help_text="Number of returning customers")
    retention_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Customer retention rate percentage"
    )