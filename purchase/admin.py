# # purchases/admin.py
# from django.contrib import admin
# from django.utils.html import format_html
# from django.urls import reverse
# from django.utils.safestring import mark_safe
# from .models import (
#     PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptItem,
#     PurchasePayment, PurchaseReturn, PurchaseReturnItem
# )


# class PurchaseOrderItemInline(admin.TabularInline):
#     """Inline for Purchase Order Items."""
#     model = PurchaseOrderItem
#     extra = 0
#     readonly_fields = ('total_cost',)
#     autocomplete_fields = ['inventory_item']
#     fields = [
#         'inventory_item', 'quantity', 'unit_price', 'total_cost',
#         'received_quantity', 'notes'
#     ]


# @admin.register(PurchaseOrder)
# class PurchaseOrderAdmin(admin.ModelAdmin):
#     """Admin for Purchase Orders."""
#     list_display = [
#         'po_number', 'supplier', 'order_date', 'status', 'payment_status',
#         'total_amount', 'total_items', 'created_by'
#     ]
#     list_filter = [
#         'status', 'payment_status', 'order_date', 'created_at',
#         'supplier', 'created_by'
#     ]
#     search_fields = ['po_number', 'supplier__name', 'notes']
#     readonly_fields = [
#         'po_number', 'subtotal', 'total_amount', 'total_items',
#         'total_quantity', 'created_at', 'updated_at'
#     ]
#     autocomplete_fields = ['supplier', 'created_by']
#     inlines = [PurchaseOrderItemInline]

#     # ✅ include custom actions here
#     actions = ['mark_as_sent', 'mark_as_confirmed']

#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'po_number', 'supplier', 'order_date', 'expected_delivery_date'
#             )
#         }),
#         ('Status', {
#             'fields': ('status', 'payment_status')
#         }),
#         ('Financial Details', {
#             'fields': (
#                 'subtotal', 'tax_amount', 'discount_amount', 'total_amount'
#             )
#         }),
#         ('Additional Information', {
#             'fields': ('notes', 'terms_and_conditions')
#         }),
#         ('Metadata', {
#             'fields': (
#                 'created_by', 'total_items', 'total_quantity',
#                 'created_at', 'updated_at'
#             ),
#             'classes': ('collapse',)
#         })
#     )

#     def total_items(self, obj):
#         return obj.total_items
#     total_items.short_description = 'Items'

#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         return queryset.select_related('supplier', 'created_by')

#     # ✅ attach action methods to the class
#     def mark_as_sent(self, request, queryset):
#         """Mark selected purchase orders as sent."""
#         updated = queryset.filter(status='draft').update(status='sent')
#         self.message_user(request, f'{updated} purchase orders marked as sent.')
#     mark_as_sent.short_description = "Mark selected orders as sent to supplier"

#     def mark_as_confirmed(self, request, queryset):
#         """Mark selected purchase orders as confirmed."""
#         updated = queryset.filter(status='sent').update(status='confirmed')
#         self.message_user(request, f'{updated} purchase orders marked as confirmed.')
#     mark_as_confirmed.short_description = "Mark selected orders as confirmed"

# class PurchaseReceiptItemInline(admin.TabularInline):
#     """Inline for Purchase Receipt Items."""
#     model = PurchaseReceiptItem
#     extra = 0
#     readonly_fields = ('purchase_order_item',)
#     fields = [
#         'purchase_order_item', 'received_quantity', 'accepted_quantity',
#         'rejected_quantity', 'status', 'unit_price', 'notes', 'rejection_reason'
#     ]


# @admin.register(PurchaseReceipt)
# class PurchaseReceiptAdmin(admin.ModelAdmin):
#     """Admin for Purchase Receipts."""
#     list_display = [
#         'receipt_number', 'purchase_order', 'supplier_name', 'receipt_date',
#         'status', 'received_by'
#     ]
#     list_filter = [
#         'status', 'receipt_date', 'created_at', 'received_by'
#     ]
#     search_fields = ['receipt_number', 'purchase_order__po_number', 'purchase_order__supplier__name']
#     readonly_fields = ['receipt_number', 'created_at', 'updated_at']
#     autocomplete_fields = ['purchase_order', 'received_by']
#     inlines = [PurchaseReceiptItemInline]
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'receipt_number', 'purchase_order', 'receipt_date'
#             )
#         }),
#         ('Supplier Invoice', {
#             'fields': ('supplier_invoice_number', 'supplier_invoice_date')
#         }),
#         ('Status & Processing', {
#             'fields': ('status', 'received_by', 'notes')
#         }),
#         ('Metadata', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def supplier_name(self, obj):
#         return obj.purchase_order.supplier.name
#     supplier_name.short_description = 'Supplier'
    
#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         return queryset.select_related('purchase_order__supplier', 'received_by')


# @admin.register(PurchasePayment)
# class PurchasePaymentAdmin(admin.ModelAdmin):
#     """Admin for Purchase Payments."""
#     list_display = [
#         'purchase_order', 'supplier_name', 'payment_date', 'amount',
#         'payment_method', 'paid_by'
#     ]
#     list_filter = [
#         'payment_method', 'payment_date', 'created_at', 'paid_by'
#     ]
#     search_fields = [
#         'purchase_order__po_number', 'purchase_order__supplier__name',
#         'reference_number'
#     ]
#     readonly_fields = ['created_at']
#     autocomplete_fields = ['purchase_order', 'paid_by']
    
#     fieldsets = (
#         ('Payment Information', {
#             'fields': (
#                 'purchase_order', 'payment_date', 'amount', 'payment_method'
#             )
#         }),
#         ('Reference & Notes', {
#             'fields': ('reference_number', 'notes')
#         }),
#         ('Metadata', {
#             'fields': ('paid_by', 'created_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def supplier_name(self, obj):
#         return obj.purchase_order.supplier.name
#     supplier_name.short_description = 'Supplier'
    
#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         return queryset.select_related('purchase_order__supplier', 'paid_by')


# class PurchaseReturnItemInline(admin.TabularInline):
#     """Inline for Purchase Return Items."""
#     model = PurchaseReturnItem
#     extra = 0
#     readonly_fields = ('total_amount',)
#     autocomplete_fields = ['inventory_item']
#     fields = [
#         'inventory_item', 'quantity', 'unit_price', 'total_amount', 'reason'
#     ]


# @admin.register(PurchaseReturn)
# class PurchaseReturnAdmin(admin.ModelAdmin):
#     """Admin for Purchase Returns."""
#     list_display = [
#         'return_number', 'purchase_order', 'supplier_name', 'return_date',
#         'status', 'total_return_amount', 'requested_by'
#     ]
#     list_filter = [
#         'status', 'return_date', 'created_at', 'requested_by', 'approved_by'
#     ]
#     search_fields = [
#         'return_number', 'purchase_order__po_number',
#         'purchase_order__supplier__name', 'reason'
#     ]
#     readonly_fields = [
#         'return_number', 'total_return_amount', 'created_at', 'updated_at'
#     ]
#     autocomplete_fields = ['purchase_order', 'requested_by', 'approved_by']
#     inlines = [PurchaseReturnItemInline]
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'return_number', 'purchase_order', 'return_date', 'reason'
#             )
#         }),
#         ('Status & Approval', {
#             'fields': ('status', 'requested_by', 'approved_by')
#         }),
#         ('Financial', {
#             'fields': ('total_return_amount',)
#         }),
#         ('Metadata', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def supplier_name(self, obj):
#         return obj.purchase_order.supplier.name
#     supplier_name.short_description = 'Supplier'
    
#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         return queryset.select_related(
#             'purchase_order__supplier', 'requested_by', 'approved_by'
#         )


# # Register individual item models for detailed management
# @admin.register(PurchaseOrderItem)
# class PurchaseOrderItemAdmin(admin.ModelAdmin):
#     """Admin for Purchase Order Items."""
#     list_display = [
#         'purchase_order', 'inventory_item', 'quantity', 'unit_price',
#         'total_cost', 'received_quantity', 'pending_quantity'
#     ]
#     list_filter = ['purchase_order__status', 'created_at']
#     search_fields = [
#         'purchase_order__po_number', 'inventory_item__name',
#         'inventory_item__sku'
#     ]
#     readonly_fields = ['total_cost', 'pending_quantity', 'is_fully_received']
#     autocomplete_fields = ['purchase_order', 'inventory_item']
    
#     def pending_quantity(self, obj):
#         return obj.pending_quantity
#     pending_quantity.short_description = 'Pending Qty'


# @admin.register(PurchaseReceiptItem)
# class PurchaseReceiptItemAdmin(admin.ModelAdmin):
#     """Admin for Purchase Receipt Items."""
#     list_display = [
#         'receipt', 'inventory_item_name', 'received_quantity',
#         'accepted_quantity', 'rejected_quantity', 'status'
#     ]
#     list_filter = ['status', 'created_at']
#     search_fields = [
#         'receipt__receipt_number', 'purchase_order_item__inventory_item__name'
#     ]
#     autocomplete_fields = ['receipt', 'purchase_order_item']
    
#     def inventory_item_name(self, obj):
#         return obj.purchase_order_item.inventory_item.name
#     inventory_item_name.short_description = 'Item Name'


# @admin.register(PurchaseReturnItem)
# class PurchaseReturnItemAdmin(admin.ModelAdmin):
#     """Admin for Purchase Return Items."""
#     list_display = [
#         'purchase_return', 'inventory_item', 'quantity',
#         'unit_price', 'total_amount'
#     ]
#     list_filter = ['purchase_return__status', 'created_at']
#     search_fields = [
#         'purchase_return__return_number', 'inventory_item__name',
#         'inventory_item__sku'
#     ]
#     readonly_fields = ['total_amount']
#     autocomplete_fields = ['purchase_return', 'inventory_item']


# # Custom admin actions
# def mark_as_sent(modeladmin, request, queryset):
#     """Mark selected purchase orders as sent."""
#     updated = queryset.filter(status='draft').update(status='sent')
#     modeladmin.message_user(request, f'{updated} purchase orders marked as sent.')

# mark_as_sent.short_description = "Mark selected orders as sent to supplier"


# def mark_as_confirmed(modeladmin, request, queryset):
#     """Mark selected purchase orders as confirmed."""
#     updated = queryset.filter(status='sent').update(status='confirmed')
#     modeladmin.message_user(request, f'{updated} purchase orders marked as confirmed.')

# mark_as_confirmed.short_description = "Mark selected orders as confirmed"


# # Add actions to PurchaseOrderAdmin
# # PurchaseOrderAdmin.actions = [mark_as_sent, mark_as_confirmed]


# # Custom admin site configuration
# admin.site.site_header = "Purchase Management System"
# admin.site.site_title = "Purchase Admin"
# admin.site.index_title = "Welcome to Purchase Management"