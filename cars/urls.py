# cars/urls.py

from rest_framework.routers import DefaultRouter
from .views import CarViewSet, JobEntryViewSet, ServiceViewSet, CarServiceRecordViewSet, InventoryUsageViewSet

router = DefaultRouter()
router.register(r'car', CarViewSet)
router.register(r'job-entries', JobEntryViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'service-records', CarServiceRecordViewSet)
router.register(r'inventory-usage', InventoryUsageViewSet, basename='inventory-usage')

urlpatterns = router.urls
