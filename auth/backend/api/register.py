from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        name = request.data.get("name")  # Alteração correta
        last_name = request.data.get("last_name")  # Alteração correta
        email = request.data.get("email")  # Adicionado
        setor = request.data.get("setor")  # Adicionado

        if not username or not password or not name or not last_name or not email or not setor:
            return Response({"detail": "Todos os campos são obrigatórios!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Usuário já existe!"}, status=status.HTTP_400_BAD_REQUEST)

        # Criação do usuário
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=name,
            last_name=last_name,
            email=email
        )
        user.setor = setor  # Se for necessário armazenar o setor em outro lugar, como em um Profile.
        user.save()

        return Response({"detail": "Usuário registrado com sucesso!"}, status=status.HTTP_201_CREATED)
