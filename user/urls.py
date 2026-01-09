from django.urls import path
from .views import RegisterView, LoginView, RefreshCookieView, LogoutView, VerifyEmailView, MeView, csrf

urlpatterns = [
    path("csrf/", csrf, name="csrf"),
    path('register/', RegisterView.as_view(), name='api_register'),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshCookieView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
