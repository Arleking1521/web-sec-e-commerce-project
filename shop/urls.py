from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register("brands", BrandViewSet)
router.register("categories", CategoryViewSet)
router.register("products", ProductViewSet)
router.register("product-images", ProductImageViewSet)
router.register("cart", CartViewSet, basename="cart")
router.register("cart-items", CartItemViewSet, basename="cart-items")
router.register("orders", OrderViewSet, basename="orders")

urlpatterns = router.urls
