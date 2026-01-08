from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError

from .models import *
from .serializers import *
from .filters import ProductFilter

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter

    search_fields = ["name", "description", "sku", "brand__name", "category__name"]

    ordering_fields = ["price", "name", "quantity", "id"]
    ordering = ["-id"]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        brand = self.request.query_params.get("brand")

        if category:
            qs = qs.filter(category__id=category)
        if brand:
            qs = qs.filter(brand__id=brand)

        return qs

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.AllowAny]


class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)

        product = serializer.validated_data.get("product")
        qty = serializer.validated_data.get("quantity", 1)

        if qty <= 0:
            raise ValidationError({"quantity": "Количество должно быть больше 0"})

        item = CartItem.objects.filter(cart=cart, product=product).first()

        if item:
            item.quantity += qty
            item.save(update_fields=["quantity"])
            
            serializer.instance = item
        else:
            serializer.save(cart=cart)

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    @action(detail=False, methods=["post"])
    def from_cart(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        items = cart.cartitem_set.all()

        if not items.exists():
            return Response(
                {"detail": "Корзина пуста"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.create(
            user=request.user,
            shipping_address=request.data.get("shipping_address"),
            delivery_method=request.data.get("delivery_method"),
            total_amount=0
        )

        total = 0
        for item in items:
            order_item = order.items.create(
                product=item.product,
                quantity=item.quantity
            )
            total += order_item.subtotal

        order.total_amount = total
        order.save()

        items.delete()  # очистка корзины

        return Response(OrderSerializer(order).data, status=201)
