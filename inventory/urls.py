from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet, SupplierViewSet, ProductCategoryViewSet

router = DefaultRouter()
router.register(r'product', InventoryItemViewSet, basename='inventory')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'categories', ProductCategoryViewSet, basename='productcategory')
urlpatterns = router.urls
