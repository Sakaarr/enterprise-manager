from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BillViewSet, BillLineItemViewSet, PaymentViewSet,BillSummaryView

router = DefaultRouter()
router.register("bills", BillViewSet)
router.register("bill-line-items", BillLineItemViewSet)
router.register("payments", PaymentViewSet)

urlpatterns = router.urls
urlpatterns += [
    path("summary/", BillSummaryView.as_view(), name="bill-summary"),
]