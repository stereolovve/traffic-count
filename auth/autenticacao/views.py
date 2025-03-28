# auth/autenticacao/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework import status
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .serializers import RegistroSerializer
from .models import User
import logging, json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Usuário e senha são obrigatórios!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "setor": user.setor,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Credenciais inválidas!"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print(f"🔍 Recebendo payload de registro: {request.data}")  # ✅ Debug

        username = request.data.get("username")
        password = request.data.get("password")
        name = request.data.get("name")
        last_name = request.data.get("last_name")
        email = request.data.get("email")
        setor = request.data.get("setor")

        if not username or not password or not name or not last_name or not email or not setor:
            return Response({"detail": "Todos os campos são obrigatórios!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Usuário já existe!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"detail": "E-mail já cadastrado!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=name,
                last_name=last_name,
                email=email
            )
            user.setor = setor
            user.save()

            print(f"✅ Usuário criado com sucesso: {user}")  # ✅ Debug
            return Response(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "setor": user.setor,
                    "detail": "Usuário registrado com sucesso!"
                }, 
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print(f"❌ ERRO AO CRIAR USUÁRIO: {e}")  # ✅ Log do erro
            return Response({"detail": f"Erro ao registrar usuário: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist() 

            tokens = OutstandingToken.objects.filter(user=request.user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)

            return Response({"detail": "Logout realizado com sucesso."})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token é obrigatório!"}, status=400)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({"access": access_token})
        except Exception as e:
            return Response({"detail": "Token inválido ou expirado!"}, status=401)
