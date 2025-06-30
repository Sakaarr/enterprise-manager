# cars/urls.py

from rest_framework.routers import DefaultRouter
from .views import CarViewSet, JobEntryViewSet, ServiceViewSet, CarServiceRecordViewSet

router = DefaultRouter()
router.register(r'cars', CarViewSet)
router.register(r'job-entries', JobEntryViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'service-records', CarServiceRecordViewSet)

urlpatterns = router.urls
