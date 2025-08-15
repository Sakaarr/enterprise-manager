from django.urls import path
from .views import (
    BillCalculationAPIView, 
    InvoicePDFView, 
    BillListAPIView,
    BillDetailAPIView, 
    BillUpdateAPIView, 
    BillDeleteAPIView,
    BillSearchAPIView,
    PaidBillListAPIView
)

urlpatterns = [
    # Bill calculation and PDF generation (unchanged)
    path('cars/bill/calculate/', BillCalculationAPIView.as_view(), name='bill-calculate'),
    path('cars/billing/generatepdf', InvoicePDFView.as_view(), name='pdf'),
    
    # Bill management with car search capabilities
    path('billing/bills/', BillListAPIView.as_view(), name='bill-list'),
    path('billing/bills/search/', BillSearchAPIView.as_view(), name='bill-search'),
    path('billing/bills/<int:bill_id>/', BillDetailAPIView.as_view(), name='bill-detail'),
    path('billing/bills/<int:bill_id>/update/', BillUpdateAPIView.as_view(), name='bill-update'),
    path('billing/bills/<int:bill_id>/delete/', BillDeleteAPIView.as_view(), name='bill-delete'),
    path('paid-bills/', PaidBillListAPIView.as_view(), name='paid-bill-list'),
]