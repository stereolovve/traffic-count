# auth/backend/api/login.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

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
