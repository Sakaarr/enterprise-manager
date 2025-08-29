# cars/urls.py

from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import CarViewSet, JobEntryViewSet, ServiceViewSet, CarServiceRecordViewSet,GatePassPDFView, InventoryUsageViewSet

router = DefaultRouter()
router.register(r'car', CarViewSet)
router.register(r'job-entries', JobEntryViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'service-records', CarServiceRecordViewSet)
router.register(r'inventory-usage', InventoryUsageViewSet, basename='inventory-usage')
urlpatterns = [
    path('gate-pass/<int:jobentry_id>/', GatePassPDFView.as_view(), name='gate-pass-pdf'),
]

urlpatterns+= router.urls
