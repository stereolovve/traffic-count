import flet as ft
from database import Session, Categoria, Sessao, Contagem, Historico, init_db  # Importar os modelos e sessão do arquivo database.py
def criar_sessao(self, e):
    if not self.validar_campos():
        return

    try:
        self.session.query(Sessao).delete()  # Deletar todas as sessões anteriores
        self.session.commit()

        self.detalhes = {
            "Pesquisador": self.pesquisador_input.value,
            "Código": self.codigo_ponto_input.value,
            "Ponto": self.nome_ponto_input.value,
            "Periodo": self.horas_contagem_input.value,
            "Data do Ponto": self.data_ponto_input.value,
            "Movimentos": [mov.controls[0].value for mov in self.movimentos_container.controls]
        }
        self.sessao = f"{self.detalhes['Código']}_{self.detalhes['Ponto']}_{self.detalhes['Data do Ponto']}"
        self.salvar_sessao()
        self.carregar_categorias_padrao('padrao.json')
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.setup_aba_contagem()

        # Notificação visual usando snackbar
        snackbar = ft.SnackBar(ft.Text("Sessão criada com sucesso!"), bgcolor="GREEN")
        self.page.overlay.append(snackbar)
        snackbar.open = True

        self.tabs.selected_index = 1
        self.tabs.tabs[1].content.visible = True
        self.update_sessao_status()
    except Exception as ex:
        print(f"Erro ao criar sessão: {ex}")
        
            
def confirmar_finalizar_sessao(self, e):
    """Diálogo de confirmação para finalizar a sessão"""
    def close_dialog(e):
        dialog.open = False
        self.page.update()

    def end_and_close(e):
        dialog.open = False
        self.page.update()
        self.end_session()

    dialog = ft.AlertDialog(
        title=ft.Text("Finalizar Sessão"),
        content=ft.Text("Você tem certeza que deseja finalizar a sessão?"),
        actions=[
            ft.TextButton("Sim", on_click=end_and_close),
            ft.TextButton("Cancelar", on_click=close_dialog),
        ],
    )
    self.page.overlay.append(dialog)
    dialog.open = True
    self.page.update()
    
    
def end_session(self):
    try:
        self.finalizar_sessao()  # Marca a sessão como finalizada no banco de dados
        
        # Limpa a sessão ativa
        self.sessao = None
        self.detalhes = {"Movimentos": []}
        self.contagens = {}
        self.binds = {}
        self.labels = {}

        # Notificação ao finalizar
        snackbar = ft.SnackBar(ft.Text("Sessão finalizada!"), bgcolor="BLUE")
        self.page.overlay.append(snackbar)
        snackbar.open = True

        # Reinicia o aplicativo
        self.restart_app()
    except Exception as ex:
        print(f"Erro ao finalizar sessão: {ex}")