from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Category)
admin.site.register(Brand)
# admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Cart)
# admin.site.register(CartItem)
admin.site.register(Order)
# admin.site.register(OrderItem)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # сколько пустых форм показывать
    fields = ("image", "name")

@admin.register(Product)
class CustomProductAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Main info', {'fields': ('sku', 'name', 'description', 'price', 'is_active')}),
        ('Additional information', {'fields': ('quantity', 'category', 'brand')}),
    )
    add_fieldsets = (
        ('Main info', {'fields': ('sku', 'name', 'description', 'price', )}),
        ('Additional information', {'fields': ('quantity', 'category', 'brand')}),
    )
    list_display = ('sku', 'name', 'quantity', 'price', 'is_active')
    search_fields = ('sku', 'name', 'price', 'brand__name', 'category__name')
    ordering = ('sku',)
    list_filter = ('is_active', 'brand', 'category')
    list_per_page = 20
    save_on_top = True
    inlines = [ProductImageInline]

    actions = ['make_active', 'make_unactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    def make_unactive(self, request, queryset):
        queryset.update(is_active=False)

    def get_fieldsets(self, request, obj=None):
        if obj:
            return self.fieldsets
        return self.add_fieldsets
    
@admin.register(CartItem)
class CustomCartItemsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Cart info', {'fields': ('cart', 'total_item_price',)}),
        ('Selected product', {'fields': ('product', 'quantity', 'unit_price',)}),
    )
    add_fieldsets = (
        ('Cart info', {'fields': ('cart',)}),
        ('Selected product', {'fields': ('product', 'quantity')}),
    )
    list_display = ('cart__user__username', 'product__name', 'quantity', 'total_item_price')
    search_fields = ('cart__user__username', 'product__sku', 'product__name',)
    readonly_fields = ('total_item_price', 'unit_price')
    list_per_page = 20
    save_on_top = True

    def get_fieldsets(self, request, obj=None):
        if obj:
            return self.fieldsets
        return self.add_fieldsets
    
@admin.register(OrderItem)
class CustomOrderItemsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Cart info', {'fields': ('order', 'subtotal',)}),
        ('Selected product', {'fields': ('product', 'quantity', 'unit_price',)}),
    )
    add_fieldsets = (
        ('Cart info', {'fields': ('order',)}),
        ('Selected product', {'fields': ('product', 'quantity')}),
    )
    list_display = ('order__user__username', 'product__name', 'quantity', 'subtotal')
    search_fields = ('order__user__username', 'product__sku', 'product__name',)
    readonly_fields = ('subtotal', 'unit_price')
    list_per_page = 20
    save_on_top = True

    def get_fieldsets(self, request, obj=None):
        if obj:
            return self.fieldsets
        return self.add_fieldsets