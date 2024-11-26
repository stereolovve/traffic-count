from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from .serializers import RegistroSerializer
from .models import User


from django.contrib.auth import authenticate

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Usuário e senha são obrigatórios!'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)

        return Response(
            {'detail': 'Credenciais inválidas!'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Logs para monitorar os dados recebidos

        # Capturar os campos
        username = request.data.get("username")
        password = request.data.get("password")
        name = request.data.get("name")
        last_name = request.data.get("last_name")
        email = request.data.get("email")
        setor = request.data.get("setor")

        # Validação de campos obrigatórios
        if not username or not password or not name or not last_name or not email or not setor:
            return Response({"detail": "Todos os campos são obrigatórios!"}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar se o usuário já existe
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Usuário já existe!"}, status=status.HTTP_400_BAD_REQUEST)

        # Criar usuário
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=name,
            last_name=last_name,
            email=email
        )
        user.setor = setor  # Setar o setor se necessário
        user.save()

        return Response({"detail": "Usuário registrado com sucesso!"}, status=status.HTTP_201_CREATED)



class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # Adiciona à blacklist (se configurado)
            return Response({"detail": "Logout realizado com sucesso."})
        except Exception as e:
            return Response({"error": str(e)}, status=400)