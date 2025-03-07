# auth/backend/api/register.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

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

