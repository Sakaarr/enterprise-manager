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