from rest_framework import serializers
from decimal import Decimal


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
    """Serializer for bill calculation response"""
    bill_id = serializers.IntegerField(help_text="Generated bill ID")
    total_service_cost = serializers.CharField(help_text="Total cost of services")
    total_inventory_cost = serializers.CharField(help_text="Total cost of inventory/products")
    total_amount = serializers.CharField(help_text="Total bill amount before discount and payment")
    discount = serializers.CharField(help_text="Applied discount amount")
    amount_paid = serializers.CharField(help_text="Amount already paid")
    amount_remaining = serializers.CharField(help_text="Remaining amount to be paid")
    created_at = serializers.CharField(help_text="Bill creation timestamp")
