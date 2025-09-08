# purchases/serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import (
    PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptItem,
    PurchasePayment, PurchaseReturn, PurchaseReturnItem
)
from inventory.models import Supplier, InventoryItem
from users.models import User


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    inventory_item_unit = serializers.CharField(source='inventory_item.unit', read_only=True)
    inventory_item_sku = serializers.CharField(source='inventory_item.sku', read_only=True)
    pending_quantity = serializers.ReadOnlyField()
    is_fully_received = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'inventory_item', 'inventory_item_name', 'inventory_item_unit', 
            'inventory_item_sku', 'quantity', 'unit_price', 'total_cost', 
            'notes', 'received_quantity', 'pending_quantity', 'is_fully_received',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['total_cost']


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_items = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'order_date',
            'expected_delivery_date', 'status', 'payment_status', 'total_amount',
            'total_items', 'total_quantity', 'created_by_name', 'created_at'
        ]


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_details = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'supplier_details',
            'order_date', 'expected_delivery_date', 'status', 'payment_status',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount',
            'notes', 'terms_and_conditions', 'created_by', 'created_by_name',
            'items', 'total_items', 'total_quantity', 'created_at', 'updated_at'
        ]
        read_only_fields = ['po_number', 'subtotal', 'total_amount']

    def get_supplier_details(self, obj):
        return {
            'contact_person': obj.supplier.contact_person,
            'phone_number': obj.supplier.phone_number,
            'email': obj.supplier.email,
            'address': obj.supplier.address
        }


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'expected_delivery_date', 'tax_amount', 'discount_amount',
            'notes', 'terms_and_conditions', 'items'
        ]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['created_by'] = self.context['request'].user
        
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
        
        purchase_order.calculate_totals()
        return purchase_order

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        # Update PO fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            # Delete existing items
            instance.items.all().delete()
            
            # Create new items
            for item_data in items_data:
                PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
        
        instance.calculate_totals()
        return instance


class PurchaseReceiptItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='purchase_order_item.inventory_item.name', read_only=True)
    inventory_item_unit = serializers.CharField(source='purchase_order_item.inventory_item.unit', read_only=True)
    ordered_quantity = serializers.IntegerField(source='purchase_order_item.quantity', read_only=True)

    class Meta:
        model = PurchaseReceiptItem
        fields = [
            'id', 'purchase_order_item', 'inventory_item_name', 'inventory_item_unit',
            'ordered_quantity', 'received_quantity', 'accepted_quantity', 'rejected_quantity',
            'status', 'unit_price', 'notes', 'rejection_reason', 'created_at', 'updated_at'
        ]


class PurchaseReceiptListSerializer(serializers.ModelSerializer):
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)

    class Meta:
        model = PurchaseReceipt
        fields = [
            'id', 'receipt_number', 'purchase_order', 'purchase_order_number',
            'supplier_name', 'receipt_date', 'supplier_invoice_number',
            'supplier_invoice_date', 'status', 'received_by_name', 'created_at'
        ]


class PurchaseReceiptDetailSerializer(serializers.ModelSerializer):
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)
    items = PurchaseReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseReceipt
        fields = [
            'id', 'receipt_number', 'purchase_order', 'purchase_order_number',
            'supplier_name', 'receipt_date', 'supplier_invoice_number',
            'supplier_invoice_date', 'status', 'received_by', 'received_by_name',
            'notes', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['receipt_number']


class PurchaseReceiptCreateSerializer(serializers.ModelSerializer):
    items = PurchaseReceiptItemSerializer(many=True)

    class Meta:
        model = PurchaseReceipt
        fields = [
            'purchase_order', 'supplier_invoice_number', 'supplier_invoice_date',
            'status', 'notes', 'items'
        ]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['received_by'] = self.context['request'].user
        
        receipt = PurchaseReceipt.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseReceiptItem.objects.create(receipt=receipt, **item_data)
        
        return receipt


class PurchasePaymentSerializer(serializers.ModelSerializer):
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.get_full_name', read_only=True)

    class Meta:
        model = PurchasePayment
        fields = [
            'id', 'purchase_order', 'purchase_order_number', 'supplier_name',
            'payment_date', 'amount', 'payment_method', 'reference_number',
            'notes', 'paid_by', 'paid_by_name', 'created_at'
        ]
        read_only_fields = ['paid_by', 'paid_by_name']

    def create(self, validated_data):
        validated_data['paid_by'] = self.context['request'].user
        return super().create(validated_data)


class PurchaseReturnItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    inventory_item_unit = serializers.CharField(source='inventory_item.unit', read_only=True)
    inventory_item_sku = serializers.CharField(source='inventory_item.sku', read_only=True)

    class Meta:
        model = PurchaseReturnItem
        fields = [
            'id', 'inventory_item', 'inventory_item_name', 'inventory_item_unit',
            'inventory_item_sku', 'quantity', 'unit_price', 'total_amount',
            'reason', 'created_at'
        ]
        read_only_fields = ['total_amount']


class PurchaseReturnListSerializer(serializers.ModelSerializer):
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReturn
        fields = [
            'id', 'return_number', 'purchase_order', 'purchase_order_number',
            'supplier_name', 'return_date', 'status', 'total_return_amount',
            'total_items', 'requested_by_name', 'created_at'
        ]

    def get_total_items(self, obj):
        return obj.items.count()


class PurchaseReturnDetailSerializer(serializers.ModelSerializer):
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    items = PurchaseReturnItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseReturn
        fields = [
            'id', 'return_number', 'purchase_order', 'purchase_order_number',
            'supplier_name', 'return_date', 'reason', 'status', 'total_return_amount',
            'requested_by', 'requested_by_name', 'approved_by', 'approved_by_name',
            'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['return_number', 'total_return_amount', 'requested_by']


class PurchaseReturnCreateSerializer(serializers.ModelSerializer):
    items = PurchaseReturnItemSerializer(many=True)

    class Meta:
        model = PurchaseReturn
        fields = ['purchase_order', 'reason', 'items']

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['requested_by'] = self.context['request'].user
        
        purchase_return = PurchaseReturn.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseReturnItem.objects.create(purchase_return=purchase_return, **item_data)
        
        return purchase_return


# Analytics Serializers
class PurchaseAnalyticsSerializer(serializers.Serializer):
    total_purchase_orders = serializers.IntegerField()
    total_purchase_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_payments_made = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_returns = serializers.IntegerField()
    total_return_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class SupplierPurchaseStatsSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField()
    supplier_name = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_order_date = serializers.DateField()


class MonthlyPurchaseTrendSerializer(serializers.Serializer):
    month = serializers.CharField()
    year = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_quantity = serializers.IntegerField()