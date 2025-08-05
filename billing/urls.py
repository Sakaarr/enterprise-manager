from django.urls import path
from .views import BillCalculationAPIView, InvoicePDFView

urlpatterns = [
    path('cars/bill/calculate/', BillCalculationAPIView.as_view(), name='bill-calculate'),
    path('cars/billing/generatepdf', InvoicePDFView.as_view(),name='pdf')
]
