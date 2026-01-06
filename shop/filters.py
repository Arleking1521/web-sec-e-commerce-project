# shop/filters.py (или где у тебя Product)
import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    brand = django_filters.NumberFilter(field_name="brand_id")
    sku = django_filters.CharFilter(field_name="sku", lookup_expr="iexact")

    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "brand", "sku", "price_min", "price_max"]
