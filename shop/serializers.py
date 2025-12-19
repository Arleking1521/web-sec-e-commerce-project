# serializers.py
from rest_framework import serializers
from .models import *


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "name", "product"]
        read_only_fields = ["id"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(source="productimage_set", many=True, read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source="brand", write_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "price", "description", "is_active", "sku", "quantity",
            "category", "brand", "images",
            "category_id", "brand_id",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", write_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id", "cart", "product", "product_id",
            "quantity", "unit_price", "total_item_price",
        ]
        read_only_fields = ["unit_price", "total_item_price"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Количество должно быть >= 1.")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source="cartitem_set", many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "items"]
        read_only_fields = ["id"]


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product", "product_id", "quantity", "unit_price", "subtotal"]
        read_only_fields = ["unit_price", "subtotal"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Количество должно быть >= 1.")
        return value


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "user", "status", "total_amount", "created_at",
            "shipping_address", "delivery_method", "items",
        ]
        read_only_fields = ["created_at"]


# Если хочешь создавать заказ вместе с позициями одним запросом (nested create):
class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "user", "status", "shipping_address", "delivery_method", "total_amount", "items"]
        read_only_fields = ["id", "status", "total_amount"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)

        total = 0
        for item in items_data:
            # product уже будет в item["product"] из product_id field (source="product")
            order_item = OrderItem.objects.create(order=order, **item)
            total += order_item.subtotal

        order.total_amount = total
        order.save(update_fields=["total_amount"])
        return order
