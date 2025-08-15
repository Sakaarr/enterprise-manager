from django.urls import path
from .views import (
    BillCalculationAPIView, 
    InvoicePDFView, 
    BillListAPIView,
    BillDetailAPIView, 
    BillUpdateAPIView, 
    BillDeleteAPIView,
    BillSearchAPIView,
    PaidBillListAPIView,
    RevenueAnalyticsAPIView,
    PaymentAnalyticsAPIView,
    TopCustomersAPIView,
    DashboardSummaryAPIView,
    ServiceAnalyticsAPIView,
    InventoryAnalyticsAPIView,
    MonthlyComparisonAPIView,
    PaymentStatusSummaryAPIView,
    PeakHoursAnalyticsAPIView,
    CustomerRetentionAPIView
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
    # Revenue Analytics
    path('revenue/', RevenueAnalyticsAPIView.as_view(), name='revenue-analytics'),
    
    # Payment Analytics
    path('payments/', PaymentAnalyticsAPIView.as_view(), name='payment-analytics'),
    
    # Customer Analytics
    path('top-customers/', TopCustomersAPIView.as_view(), name='top-customers'),
    
    
    # Time-based Analytics
    
    # Dashboard
    path('dashboard-summary/', DashboardSummaryAPIView.as_view(), name='dashboard-summary'),
    path('analytics/services/', ServiceAnalyticsAPIView.as_view(), name='service-analytics'),
    path('analytics/inventory/', InventoryAnalyticsAPIView.as_view(), name='inventory-analytics'),
    
    # New Analytics URLs - Comparisons & Status
    path('analytics/monthly-comparison/', MonthlyComparisonAPIView.as_view(), name='monthly-comparison'),
    path('analytics/payment-status/', PaymentStatusSummaryAPIView.as_view(), name='payment-status-summary'),
    
    # New Analytics URLs - Behavioral Analytics
    path('analytics/peak-hours/', PeakHoursAnalyticsAPIView.as_view(), name='peak-hours-analytics'),
    path('analytics/customer-retention/', CustomerRetentionAPIView.as_view(), name='customer-retention'),
]