from rest_framework import serializers
from .models import Bill, BillLineItem, Payment

class BillLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillLineItem
        fields = ["id", "description", "quantity", "rate", "amount"]

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "bill", "paid_amount", "paid_on", "payment_method"]

class BillSerializer(serializers.ModelSerializer):
    line_items = BillLineItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id", "service_record", "discount", "tax_percent",
            "total_amount", "amount_paid", "amount_due", "is_fully_paid",
            "created_at", "line_items", "payments"
        ]
