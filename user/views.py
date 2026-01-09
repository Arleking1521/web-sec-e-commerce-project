from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.http import JsonResponse
from .serializers import RegisterSerializer, LoginSerializer, MeSerializer, MeUpdateSerializer
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import generics
from django.contrib.auth import get_user_model
from .token import TokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .utils import send_verification_email
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


User = get_user_model()
acc_active_token = TokenGenerator()

@require_GET
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()

            send_verification_email(user)

            return Response(
                {"detail": "Регистрация успешна. Проверь почту и подтверди аккаунт."},
                status=status.HTTP_201_CREATED
            )

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return JsonResponse({"detail": "uid и token обязательны"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return JsonResponse({"detail": "Неверная ссылка подтверждения"}, status=status.HTTP_400_BAD_REQUEST)

        if acc_active_token.check_token(user, token):
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
            return JsonResponse({"detail": "Email подтвержден. Аккаунт активирован."}, status=status.HTTP_200_OK)

        return JsonResponse({"detail": "Токен недействителен или истёк"}, status=status.HTTP_400_BAD_REQUEST)

def _set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie(
        key=settings.JWT_AUTH_COOKIE,
        value=access,
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=settings.JWT_COOKIE_HTTPONLY,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path=settings.JWT_COOKIE_PATH,
    )
    response.set_cookie(
        key=settings.JWT_AUTH_REFRESH_COOKIE,
        value=refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=settings.JWT_COOKIE_HTTPONLY,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path=settings.JWT_COOKIE_PATH,
    )

def _clear_auth_cookies(response: Response):
    response.delete_cookie(settings.JWT_AUTH_COOKIE, path=settings.JWT_COOKIE_PATH)
    response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE, path=settings.JWT_COOKIE_PATH)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return JsonResponse(
            {"detail": "Use POST to login."},
            status=405
        )

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)

        resp = JsonResponse(
            {
                "detail": "OK",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            },
            status=status.HTTP_200_OK
        )

        _set_auth_cookies(resp, access=access, refresh=refresh_str)
        return resp


class RefreshCookieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if not refresh_token:
            return JsonResponse({"detail": "Refresh cookie not found"}, status=401)

        try:
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            # если ROTATE_REFRESH_TOKENS=True — можно выдать новый refresh
            new_refresh = str(refresh)  # текущий (или новый при ротации ниже)

            # Ротация refresh (опционально):
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                refresh.set_jti()
                refresh.set_exp()
                new_refresh = str(refresh)

            resp = JsonResponse({"detail": "OK"}, status=200)
            _set_auth_cookies(resp, access=new_access, refresh=new_refresh)
            return resp
        except Exception:
            return JsonResponse({"detail": "Invalid refresh token"}, status=401)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    # def get(self, request):
    #     resp = Response({"detail": "Logged out"}, status=200)
    #     _clear_auth_cookies(resp)
    #     return resp

    def post(self, request):
        resp = JsonResponse({"detail": "Logged out"}, status=200)
        _clear_auth_cookies(resp)
        return resp
    
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return JsonResponse(MeSerializer(request.user).data)
    
    def patch(self, request):
        serializer = MeUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        return JsonResponse(
            {
                "detail": "Профиль обновлён.",
                "user": MeSerializer(updated_user).data,
            },
            status=status.HTTP_200_OK,
        )