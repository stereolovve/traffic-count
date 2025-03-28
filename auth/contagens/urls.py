#auth/contagens/urls.py
from django.urls import path
from .views import listar_sessoes, detalhes_sessao, get_countings, finalizar_sessao, registrar_sessao

urlpatterns = [
    path('', listar_sessoes, name='listar_sessoes'),
    path('detalhes/<int:sessao_id>/', detalhes_sessao, name='detalhes_sessao'),
    path('get/', get_countings, name='get_countings'),
    path('finalizar-sessao/', finalizar_sessao, name='finalizar_sessao'),
    path('registrar-sessao/', registrar_sessao, name='registrar_sessao'),
]
