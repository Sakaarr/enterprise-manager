from django.urls import path
from .views import BillCalculationAPIView, InvoicePDFView, BillListAPIView,BillDetailAPIView, BillUpdateAPIView, BillDeleteAPIView

urlpatterns = [
    path('cars/bill/calculate/', BillCalculationAPIView.as_view(), name='bill-calculate'),
    path('cars/billing/generatepdf', InvoicePDFView.as_view(),name='pdf'),
    path('billing/bills/', BillListAPIView.as_view(), name='bill-list'),
    path('billing/bills/<int:bill_id>/', BillDetailAPIView.as_view(), name='bill-detail'),
    path('billing/bills/<int:bill_id>/update/', BillUpdateAPIView.as_view(), name='bill-update'),
    path('billing/bills/<int:bill_id>/delete/', BillDeleteAPIView.as_view(), name='bill-delete'),
]
