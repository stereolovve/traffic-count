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
from .serializers import RegistroSerializer, PadraoContagemSerializer, UserPadraoContagemSerializer
from .models import User, PadraoContagem, UserPadraoContagem

import logging, json

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import PadraoContagemForm

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


class PadraoContagemViewSet(viewsets.ModelViewSet):
    serializer_class = PadraoContagemSerializer

    def get_queryset(self):
        queryset = PadraoContagem.objects.all()
        tipo = self.request.query_params.get('pattern_type') 
        if tipo:
            queryset = queryset.filter(pattern_type=tipo)
        return queryset

class PadraoContagemListView(ListView):
    model = PadraoContagem
    template_name = 'auth/padrao_list.html'
    context_object_name = 'padroes'

class PadraoContagemCreateView(CreateView):
    model = PadraoContagem
    form_class = PadraoContagemForm
    template_name = 'auth/padrao_form.html'
    success_url = reverse_lazy('padrao_list')  

class PadraoContagemUpdateView(UpdateView):
    model = PadraoContagem
    form_class = PadraoContagemForm
    template_name = 'auth/padrao_form.html'
    success_url = reverse_lazy('padrao_list')

class PadraoContagemDeleteView(DeleteView):
    model = PadraoContagem
    template_name = 'auth/padrao_confirm_delete.html'
    success_url = reverse_lazy('padrao_list')

@api_view(['GET'])
def listar_tipos_padrao(request):
    tipos = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
    return Response(list(tipos))

@api_view(['GET'])
@permission_classes([AllowAny])
def listar_padroes_globais(request):

    padroes = PadraoContagem.objects.values('pattern_type').distinct()
    data = []

    for padrao in padroes:
        tipo_padrao = padrao["pattern_type"]
        binds = PadraoContagem.objects.filter(pattern_type=tipo_padrao).values("veiculo", "bind")
        data.append({
            "pattern_type": tipo_padrao,
            "binds": list(binds)
        })

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    """Retorna informações básicas do usuário autenticado."""
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "preferences": user.preferences
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_preferences_usuario(request):
    """Retorna os padrões personalizados do usuário ou os padrões globais."""
    user = request.user
    preferences = user.preferences if hasattr(user, 'preferences') else {}

    if not preferences:
        # 🔹 Chama diretamente a função que retorna padrões globais
        tipos_padroes = PadraoContagem.objects.values_list('pattern_type', flat=True).distinct()
        return Response(list(tipos_padroes), status=status.HTTP_200_OK)

    return Response(preferences, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_binds_usuario(request):
    user = request.user
    binds = user.preferences if hasattr(user, 'preferences') else {}

    return Response({"usuario": user.username, "binds": binds}, status=status.HTTP_200_OK)




@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def atualizar_preferences_usuario(request):
    user = request.user
    pattern_type = request.data.get("pattern_type")
    veiculo = request.data.get("veiculo")
    novo_bind = request.data.get("bind")

    if not pattern_type or not veiculo or not novo_bind:
        return Response({"detail": "Todos os campos são obrigatórios!"}, status=status.HTTP_400_BAD_REQUEST)

    preferences = user.preferences

    if pattern_type not in preferences:
        preferences[pattern_type] = {}

    preferences[pattern_type][veiculo] = novo_bind
    user.preferences = preferences
    user.save()

    return Response({"detail": "Bind atualizado com sucesso!"}, status=status.HTTP_200_OK)


class UserPadraoContagemViewSet(viewsets.ModelViewSet):
    serializer_class = UserPadraoContagemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserPadraoContagem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        pattern_type = self.request.data.get("pattern_type")
        veiculo = self.request.data.get("veiculo")
        novo_bind = self.request.data.get("bind")

        if not (pattern_type and veiculo and novo_bind):
            raise serializers.ValidationError({"error": "Dados incompletos para salvar o bind."})

        try:
            bind_existente = UserPadraoContagem.objects.get(
                user=user, pattern_type=pattern_type, veiculo=veiculo
            )
            bind_existente.bind = novo_bind
            bind_existente.save()
            return
        except UserPadraoContagem.DoesNotExist:
            serializer.save(user=user)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_or_global_padrao(request):
    logging.info(f"[DEBUG] 🛂 Usuário autenticado: {request.user}")  # Confirma que o usuário foi identificado

    if not request.user.is_authenticated:
        return Response({"detail": "Usuário não autenticado!"}, status=401)

    tipo = request.query_params.get('pattern_type')
    if not tipo:
        return Response({"detail": "Faltou o parâmetro pattern_type"}, status=400)

    globais = PadraoContagem.objects.filter(pattern_type=tipo)
    user_custom = UserPadraoContagem.objects.filter(user=request.user, pattern_type=tipo)

    global_dict = {g.veiculo: g.bind for g in globais}
    user_dict = {u.veiculo: u.bind for u in user_custom}

    merged = []
    for veiculo, bind_global in global_dict.items():
        bind_final = user_dict.get(veiculo, bind_global)
        merged.append({"veiculo": veiculo, "bind": bind_final, "pattern_type": tipo})

    for veiculo_user, bind_user in user_dict.items():
        if veiculo_user not in global_dict:
            merged.append({"veiculo": veiculo_user, "bind": bind_user, "pattern_type": tipo})

    return Response(merged, status=200)


class UserPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retorna as preferências do usuário logado."""
        return Response(request.user.preferences, status=status.HTTP_200_OK)

    def post(self, request):
        """Salva ou atualiza as preferências do usuário."""
        padrao = request.data.get("padrao")
        binds = request.data.get("binds")

        if not padrao or not isinstance(binds, dict):
            return Response({"detail": "Formato inválido!"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_preferences(padrao, binds)
        return Response({"detail": "Preferências salvas com sucesso!"}, status=status.HTTP_200_OK)