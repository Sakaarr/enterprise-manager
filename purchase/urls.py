# purchases/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PurchaseOrderViewSet, PurchaseReceiptViewSet, PurchasePaymentViewSet,
    PurchaseReturnViewSet, PurchaseAnalyticsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'receipts', PurchaseReceiptViewSet, basename='purchasereceipt')
router.register(r'payments', PurchasePaymentViewSet, basename='purchasepayment')
router.register(r'returns', PurchaseReturnViewSet, basename='purchasereturn')
router.register(r'analytics', PurchaseAnalyticsViewSet, basename='purchaseanalytics')

# URL patterns
urlpatterns = [
    # Include all router URLs
    path('purchase/', include(router.urls)),
    
    # Alternative explicit URL patterns (commented out - use router instead)
    # Purchase Orders
    # path('api/purchases/orders/', PurchaseOrderViewSet.as_view({'get': 'list', 'post': 'create'}), name='purchaseorder-list'),
    # path('api/purchases/orders/<int:pk>/', PurchaseOrderViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='purchaseorder-detail'),
    # path('api/purchases/orders/<int:pk>/send_to_supplier/', PurchaseOrderViewSet.as_view({'post': 'send_to_supplier'}), name='purchaseorder-send-to-supplier'),
    # path('api/purchases/orders/<int:pk>/confirm_order/', PurchaseOrderViewSet.as_view({'post': 'confirm_order'}), name='purchaseorder-confirm'),
    # path('api/purchases/orders/<int:pk>/cancel_order/', PurchaseOrderViewSet.as_view({'post': 'cancel_order'}), name='purchaseorder-cancel'),
    # path('api/purchases/orders/<int:pk>/summary/', PurchaseOrderViewSet.as_view({'get': 'summary'}), name='purchaseorder-summary'),
    
    # Purchase Receipts
    # path('api/purchases/receipts/', PurchaseReceiptViewSet.as_view({'get': 'list', 'post': 'create'}), name='purchasereceipt-list'),
    # path('api/purchases/receipts/<int:pk>/', PurchaseReceiptViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='purchasereceipt-detail'),
    # path('api/purchases/receipts/<int:pk>/accept_items/', PurchaseReceiptViewSet.as_view({'post': 'accept_items'}), name='purchasereceipt-accept-items'),
    # path('api/purchases/receipts/<int:pk>/reject_items/', PurchaseReceiptViewSet.as_view({'post': 'reject_items'}), name='purchasereceipt-reject-items'),
    
    # Purchase Payments
    # path('api/purchases/payments/', PurchasePaymentViewSet.as_view({'get': 'list', 'post': 'create'}), name='purchasepayment-list'),
    # path('api/purchases/payments/<int:pk>/', PurchasePaymentViewSet.as_view({'get': 'retrieve'}), name='purchasepayment-detail'),
    
    # Purchase Returns
    # path('api/purchases/returns/', PurchaseReturnViewSet.as_view({'get': 'list', 'post': 'create'}), name='purchasereturn-list'),
    # path('api/purchases/returns/<int:pk>/', PurchaseReturnViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='purchasereturn-detail'),
    # path('api/purchases/returns/<int:pk>/approve/', PurchaseReturnViewSet.as_view({'post': 'approve'}), name='purchasereturn-approve'),
    # path('api/purchases/returns/<int:pk>/process/', PurchaseReturnViewSet.as_view({'post': 'process'}), name='purchasereturn-process'),
    # path('api/purchases/returns/<int:pk>/reject/', PurchaseReturnViewSet.as_view({'post': 'reject'}), name='purchasereturn-reject'),
    
    # Analytics
    # path('api/purchases/analytics/analytics/', PurchaseAnalyticsViewSet.as_view({'get': 'analytics'}), name='purchase-analytics'),
    # path('api/purchases/analytics/supplier_stats/', PurchaseAnalyticsViewSet.as_view({'get': 'supplier_stats'}), name='purchase-supplier-stats'),
    # path('api/purchases/analytics/monthly_trends/', PurchaseAnalyticsViewSet.as_view({'get': 'monthly_trends'}), name='purchase-monthly-trends'),
]

# Main app URLs (to be included in main project)
app_name = 'purchases'