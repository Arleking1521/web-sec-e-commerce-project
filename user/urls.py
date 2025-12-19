# accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegistrationAPIView, ActivationAPIView, EmailTokenObtainPairView, LogoutAPIView

urlpatterns = [
    path('register/', RegistrationAPIView.as_view(), name='api_register'),
    path('activate/<uidb64>/<token>/', ActivationAPIView.as_view(), name='api_activate'),
    path('login/', EmailTokenObtainPairView.as_view(), name='api_login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutAPIView.as_view(), name='api_logout'),
]
