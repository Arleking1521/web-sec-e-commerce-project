import requests
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
from axes.handlers.proxy import AxesProxyHandler
from axes.utils import reset as axes_reset


User = get_user_model()
acc_active_token = TokenGenerator()

@require_GET
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        # 1) токен капчи с фронта (React)
        captcha_token = request.data.get("re_captcha_token")
        if not captcha_token:
            return Response(
                {"detail": "Отсутствует токен капчи"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) проверяем капчу у Google
        secret = getattr(settings, "RECAPTCHA_SECRET_KEY", None)
        if not secret:
            return Response(
                {"detail": "На сервере не настроен RECAPTCHA_SECRET_KEY"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            verify_response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret, "response": captcha_token},
                timeout=5
            )
            captcha_result = verify_response.json()
        except requests.RequestException:
            return Response(
                {"detail": "Не удалось проверить капчу. Попробуйте позже."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if not captcha_result.get("success"):
            return Response(
                {"detail": "Ошибка капчи. Вы робот?"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # (Опционально) если reCAPTCHA v3 — проверяем score
        min_score = getattr(settings, "RECAPTCHA_MIN_SCORE", None)
        if min_score is not None:
            score = captcha_result.get("score", 0)
            if score < float(min_score):
                return Response(
                    {"detail": "Капча не пройдена (низкий score)."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 3) обычная регистрация
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
        path=settings.JWT_COOKIE_REFRESH_PATH,
    )

def _clear_auth_cookies(response: Response):
    response.delete_cookie(settings.JWT_AUTH_COOKIE, path=settings.JWT_COOKIE_PATH)
    response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE, path=settings.JWT_COOKIE_REFRESH_PATH)



class LoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return JsonResponse({"detail": "Use POST to login."}, status=405)

    def post(self, request):
        if AxesProxyHandler.is_locked(request):
            return JsonResponse(
                {"detail": "Too many login attempts. Try later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        ser = LoginSerializer(data=request.data)

        if not ser.is_valid():
            identifier = (
                request.data.get("email")
                or request.data.get("username")
                or request.data.get("phone")
                or "unknown"
            )

            AxesProxyHandler.user_login_failed(
                sender=LoginView,
                credentials={"username": str(identifier)},
                request=request,
            )

            return JsonResponse(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = ser.validated_data["user"]

        # ✅ Безопасный reset: не передаём None
        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip:
            # если X-Forwarded-For содержит список — берём первый
            ip = ip.split(",")[0].strip()

        try:
            if ip:
                axes_reset(ip_address=ip)
            else:
                axes_reset()
        except Exception:
            # чтобы reset не валил логин (не критично)
            pass

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
                },
            },
            status=status.HTTP_200_OK
        )

        _set_auth_cookies(resp, access=access, refresh=refresh_str)
        return resp


class RefreshCookieView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if not refresh_token:
            return JsonResponse({"detail": "Refresh cookie not found"}, status=401)

        try:
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            new_refresh = str(refresh)  # текущий (или новый при ротации ниже)

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