from django.db import models
from django.contrib.auth.models import AbstractUser
from shop.models import Product
# Create your models here.

class User(AbstractUser):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True )
    pending_email = models.EmailField(null=True, blank=True) 
    wishlist = models.ManyToManyField(Product, blank=True, related_name='products')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [ 'first_name', 'last_name', 'username']
    
    def save(self, *args, **kwargs):
        if not self.username:
            email_prefix = self.email.split('@')[0]
            base_username = f"{self.first_name.lower()}_{email_prefix.lower()}"
            self.username = base_username

            counter = 1
            while User.objects.filter(username=self.username).exists():
                self.username = f"{base_username}_{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def __str__ (self) -> str:
        return f'{self.first_name} {self.last_name}: {self.email}'
    
    