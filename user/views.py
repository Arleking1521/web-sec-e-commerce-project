# accounts/views.py
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework import status, permissions
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterSerializer, LoginSerializer
from .token import TokenGenerator

User = get_user_model()
acc_active_token = TokenGenerator()

def del_inactive_users():
    check_time = timezone.now() - timedelta(minutes=15)
    inactive_users = User.objects.filter(is_active=False, date_joined__lt=check_time)
    for user in inactive_users:
        user.delete()

class RegistrationAPIView(APIView):
    """
    POST /api/auth/register/

    {
      "email": "user@example.com",
      "first_name": "User",
      "last_name": "Test",
      "password": "Qwerty123!",
      "password2": "Qwerty123!"
    }
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # чистим старых неактивных
        del_inactive_users()

        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']

        # проверяем, не существует ли уже активный пользователь с таким email
        try:
            existing = User.objects.get(email=email)
            if existing.is_active:
                return Response(
                    {'detail': 'Пользователь с такой почтой уже существует.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # если есть неактивный – удаляем, как у тебя в коде
                existing.delete()
        except User.DoesNotExist:
            pass

        user = serializer.save()  # создаёт is_active=False

        # формируем письмо с ссылкой активации
        current_site = get_current_site(request)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = acc_active_token.make_token(user)

        # можешь использовать ссылку на API или на фронт
        activation_link = f"http://{current_site.domain}/api/auth/activate/{uid}/{token}/"

        mail_subject = 'Ссылка для активации аккаунта'
        message = render_to_string('auth/acc_active_email.html', {
            'user': user,
            'domain': current_site.domain,
            'activation_link': activation_link,
        })
        email_msg = EmailMessage(mail_subject, message, to=[user.email])
        email_msg.send()

        return Response(
            {
                'detail': 'Пользователь зарегистрирован. Проверьте почту для активации аккаунта.',
            },
            status=status.HTTP_201_CREATED,
        )

class ActivationAPIView(APIView):
    """
    GET /api/auth/activate/<uidb64>/<token>/
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None:
            return Response(
                {'detail': 'Неверная ссылка активации.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # проверяем токен
        if not acc_active_token.check_token(user, token):
            return Response(
                {'detail': 'Неверный или устаревший токен.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # проверяем 15 минут
        time_elapsed = timezone.now() - user.date_joined
        if time_elapsed.total_seconds() >= 900:
            del_inactive_users()
            return Response(
                {'detail': 'Время активации истекло. Зарегистрируйтесь заново.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()

        return Response(
            {'detail': 'Аккаунт успешно активирован.'},
            status=status.HTTP_200_OK,
        )

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        # attrs содержит email и password (SimpleJWT сам их так считает)
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )

        if user is None:
            raise Exception('Неверный email или пароль.')

        if not user.is_active:
            raise Exception('Аккаунт не активирован.')

        data = super().validate(attrs)
        return data

class EmailTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    {
      "email": "user@example.com",
      "password": "Qwerty123!"
    }
    """
    serializer_class = EmailTokenObtainPairSerializer

class LogoutAPIView(APIView):
    """
    POST /api/auth/logout/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        django_logout(request)
        return Response({'detail': 'Вы вышли из системы.'}, status=status.HTTP_200_OK)
