from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin
# Register your models here.
# admin.site.register(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        ('Authorization datas', {'fields': ('email', 'pending_email', 'password', 'is_active')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'username')}),
        ('Access datas', {'fields': ('is_superuser', 'is_staff', 'groups')}),
        ('Additinaly information', {'fields': ('date_joined', 'last_login')}),
        ('Wishlist', {'fields': ('wishlist', )}),
        
    )
    add_fieldsets = (
        ('Authorization datas', {'fields': ('email', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name')}),
    )
    list_display = ('email', 'username', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    filter_horizontal = ('wishlist', 'groups')
    