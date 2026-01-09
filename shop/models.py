from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings

# Create your models here.
class Brand(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return f'{self.name}'
    
class Category(models.Model):
    name=models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            words = self.name.lower().split()
            self.slug = '-'.join(words)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'
    
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    description = models.TextField(blank=True)
    is_active= models.BooleanField(default=True)
    sku = models.CharField(max_length=50, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="products",
    )

    def __str__(self):
        return f"({self.sku}) {self.name} "
    
class ProductImage(models.Model):
    image = models.ImageField(upload_to='product_images')
    name = models.CharField(blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.name = self.image.name.split('.')[0].capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}: {self.product}'

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.user}'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True)
    total_item_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True)

    def save(self, *args, **kwargs):
        product_price = Product.objects.get(pk = self.product.pk).price
        self.unit_price = product_price
        self.total_item_price = self.unit_price*self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.cart}: {self.product} - {self.quantity}'
    
class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        PAID = "paid", "Оплачен"
        SHIPPED = "shipped", "Отправлен"
        DELIVERED = "delivered", "Доставлен"
        CANCELED = "canceled", "Отменён"

    class DeliveryMethod(models.TextChoices):
        PICKUP = "pickup", "Самовывоз"
        COURIER = "courier", "Курьер"
        POST = "post", "Почта"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField()
    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices
    )

    def __str__(self):
        return f"Заказ #{self.pk} на {self.total_amount}"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        blank=True
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        blank=True
    )

    def save(self, *args, **kwargs):
        product_price = Product.objects.get(pk = self.product.pk).price
        self.unit_price = product_price
        self.subtotal = self.unit_price*self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} x {self.quantity}"
    
