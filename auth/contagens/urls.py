#auth/contagens/urls.py
from django.urls import path
from .views import listar_sessoes, detalhes_sessao, get_countings, finalizar_sessao, registrar_sessao, exportar_csv, buscar_sessao, finalizar_por_nome

urlpatterns = [
    path('', listar_sessoes, name='listar_sessoes'),
    path('detalhes/<int:sessao_id>/', detalhes_sessao, name='detalhes_sessao'),
    path('get/', get_countings, name='get_countings'),
    path('finalizar-sessao/', finalizar_sessao, name='finalizar_sessao'),
    path('registrar-sessao/', registrar_sessao, name='registrar_sessao'),
    path('exportar-csv/<int:sessao_id>', exportar_csv, name='exportar_csv'),
    path('buscar-sessao/', buscar_sessao, name='buscar_sessao'),
    path('finalizar-por-nome/', finalizar_por_nome, name='finalizar_por_nome'),
]
