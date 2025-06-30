# cars/urls.py

from rest_framework.routers import DefaultRouter
from .views import CarViewSet, JobEntryViewSet

router = DefaultRouter()
router.register(r'cars', CarViewSet)
router.register(r'job-entries', JobEntryViewSet)

urlpatterns = router.urls
