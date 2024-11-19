import flet as ft
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db  # Importar os modelos e sessão do arquivo database.py
from sqlalchemy.exc import SQLAlchemyError
import json
import logging
from datetime import datetime
import os
from utils.padrao_contagem import carregar_categorias_padrao, carregar_padroes_selecionados
def criar_sessao(self, e):
    if not self.validar_campos():
        return

    try:
        self.session.query(Sessao).delete()  # Deletar todas as sessões anteriores
        self.session.commit()

        # Remover o prefixo "Data selecionada: " e converter o formato da data
        data_original = self.data_ponto_label.value.replace("Data selecionada: ", "")
        self.data_formatada = datetime.strptime(data_original, "%d-%m-%Y").strftime("%d-%m-%Y")

        self.detalhes = {
            "Pesquisador": self.username,
            "Código": self.codigo_ponto_input.value,
            "Ponto": self.nome_ponto_input.value,
            "Periodo": self.horas_contagem_input.value,
            "Data do Ponto": self.data_formatada,
            "Movimentos": [mov.controls[0].value for mov in self.movimentos_container.controls]
        }

        self.sessao = f"{self.detalhes['Código']}_{self.detalhes['Ponto']}_{self.data_formatada}"

        # Criar o diretório e o caminho do arquivo
        diretorio_base = r'Z:\0Pesquisa\_0ContadorDigital\Contagens'
        diretorio_pesquisador_codigo = os.path.join(diretorio_base, self.username, self.detalhes["Código"])
        if not os.path.exists(diretorio_pesquisador_codigo):
            os.makedirs(diretorio_pesquisador_codigo)

        arquivo_sessao = os.path.join(diretorio_pesquisador_codigo, f"{self.sessao}.xlsx")
        print(f"Arquivo gerado: {arquivo_sessao}")

        self.salvar_sessao()
        self.carregar_padroes_selecionados(e)
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
        logging.error(f"Erro ao criar sessão: {ex}")


            
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
        logging.error(f"Erro ao finalizar sessão: {ex}")
        
        
def carregar_sessao_ativa(self):
    try:
        sessao_ativa = self.session.query(Sessao).filter_by(ativa=True).first()
        if sessao_ativa:
            self.sessao = sessao_ativa.sessao
            self.detalhes = json.loads(sessao_ativa.detalhes)
            snackbar = ft.SnackBar(ft.Text("Sessão ativa recuperada."), bgcolor="GREEN")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.contagens, self.binds, self.categorias = self.carregar_config()
            self.setup_aba_contagem()
            self.tabs.selected_index = 1
            self.tabs.tabs[1].content.visible = True
            self.update_sessao_status()
            self.recuperar_contagens()
    except SQLAlchemyError as ex:
        logging.error(f"Erro ao carregar sessão ativa: {ex}")
        
        
def salvar_sessao(self):
    try:
        detalhes_json = json.dumps(self.detalhes)
        sessao_existente = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_existente:
            sessao_existente.detalhes = detalhes_json
            sessao_existente.ativa = True
        else:
            nova_sessao = Sessao(
                sessao=self.sessao,
                detalhes=detalhes_json,
                ativa=True
            )
            self.session.add(nova_sessao)
        self.session.commit()
    except SQLAlchemyError as ex:
        logging.error(f"Erro ao salvar sessão: {ex}")
        self.session.rollback()
        
        
def finalizar_sessao(self):
    try:
        # Primeiro, remover todas as contagens associadas à sessão
        contagens_a_remover = self.session.query(Contagem).filter_by(sessao=self.sessao).all()
        for contagem in contagens_a_remover:
            self.session.delete(contagem)

        # Em seguida, remover a própria sessão
        sessao_a_remover = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_a_remover:
            self.session.delete(sessao_a_remover)

        self.session.commit()
        logging.info(f"Sessão '{self.sessao}' e seus dados foram removidos com sucesso.")

        # Resetar contagens locais e atualizar a interface
        self.contagens.clear()
        self.binds.clear()
        self.labels.clear()
        self.sessao = None
        self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada e removida!")))
        self.page.update()

        self.restart_app()

    except Exception as ex:
        logging.error(f"Erro ao finalizar e remover sessão: {ex}")
        self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao finalizar sessão: {ex}")))
        self.session.rollback()
        self.page.update()