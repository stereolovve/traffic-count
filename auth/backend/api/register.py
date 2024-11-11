from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        name = request.data.get("name")

        if not username or not password or not name:
            return Response({"detail": "Todos os campos são obrigatórios!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Usuário já existe!"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, first_name=name)
        user.save()
        return Response({"detail": "Usuário registrado com sucesso!"}, status=status.HTTP_201_CREATED)
