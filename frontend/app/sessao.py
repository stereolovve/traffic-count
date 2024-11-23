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
        self.horarios_df = self.gerar_coluna_horarios(self.horas_contagem_input.value)

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
        padrao_selecionado = self.padrao_dropdown.value

        sessao_existente = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_existente:
            sessao_existente.detalhes = json.dumps(self.detalhes)
            sessao_existente.padrao = padrao_selecionado
            sessao_existente.ativa = True
        else:
            nova_sessao = Sessao(
                sessao=self.sessao,
                detalhes=json.dumps(self.detalhes),
                padrao=padrao_selecionado,
                ativa=True
            )
            self.session.add(nova_sessao)

        self.session.query(Categoria).delete()

        self.session.commit()

        diretorio_base = r'Z:\0Pesquisa\_0ContadorDigital\Contagens'
        diretorio_pesquisador_codigo = os.path.join(diretorio_base, self.username, self.detalhes["Código"])
        if not os.path.exists(diretorio_pesquisador_codigo):
            os.makedirs(diretorio_pesquisador_codigo)

        arquivo_sessao = os.path.join(diretorio_pesquisador_codigo, f"{self.sessao}.xlsx")
        logging.info(f"Arquivo gerado: {arquivo_sessao}")

        self.carregar_padroes_selecionados()

        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.setup_aba_contagem()

        snackbar = ft.SnackBar(ft.Text("Sessão criada com sucesso!"), bgcolor="GREEN")
        self.page.overlay.append(snackbar)
        snackbar.open = True

        self.tabs.selected_index = 1
        self.tabs.tabs[1].content.visible = True
        self.update_sessao_status()

    except FileNotFoundError as fnf_error:
        logging.error(f"Arquivo JSON ou diretório não encontrado: {fnf_error}")
        snackbar = ft.SnackBar(ft.Text(f"Erro: {fnf_error}"), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True
    except SQLAlchemyError as db_error:
        logging.error(f"Erro no banco de dados: {db_error}")
        self.session.rollback()
        snackbar = ft.SnackBar(ft.Text(f"Erro ao salvar sessão: {db_error}"), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True
    except Exception as ex:
        logging.error(f"Erro ao criar sessão: {ex}")
        snackbar = ft.SnackBar(ft.Text(f"Erro ao criar sessão: {ex}"), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True


       
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
        self.finalizar_sessao()
        
        self.sessao = None
        self.detalhes = {"Movimentos": []}
        self.contagens = {}
        self.binds = {}
        self.labels = {}

        snackbar = ft.SnackBar(ft.Text("Sessão finalizada!"), bgcolor="BLUE")
        self.page.overlay.append(snackbar)
        snackbar.open = True

        self.restart_app()
    except Exception as ex:
        logging.error(f"Erro ao finalizar sessão: {ex}")
        
        
def carregar_sessao_ativa(self):
    try:
        sessao_ativa = self.session.query(Sessao).filter_by(ativa=True).first()
        if sessao_ativa:
            logging.info(f"Sessão ativa encontrada: {sessao_ativa.sessao}")
            self.sessao = sessao_ativa.sessao
            self.detalhes = json.loads(sessao_ativa.detalhes)
            
            # Inicializar horários
            if 'Periodo' in self.detalhes:
                self.horarios_df = self.gerar_coluna_horarios(self.detalhes['Periodo'])
                self.ultima_linha_horarios = 0
            else:
                logging.error("Erro: Período não encontrado nos detalhes da sessão.")
            
            self.padrao_dropdown.value = sessao_ativa.padrao
            self.carregar_padroes_selecionados()

            self.update_binds()

            self.contagens, self.binds, self.categorias = self.carregar_config()

            self.setup_aba_contagem()

            for (veiculo, movimento), count in self.contagens.items():
                if (veiculo, movimento) in self.labels:
                    self.labels[(veiculo, movimento)].value = str(count)
            self.page.update()

            self.tabs.tabs[1].content.visible = True
            self.tabs.selected_index = 1
            self.page.update()

            self.update_sessao_status()

            logging.info("Sessão ativa carregada com sucesso.")
            return True
        else:
            logging.warning("Nenhuma sessão ativa encontrada.")
            return False
    except Exception as ex:
        logging.error(f"Erro ao carregar sessão ativa: {ex}")
        return False


        
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
        sessao_a_remover = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_a_remover:
            self.session.delete(sessao_a_remover)

        self.session.query(Contagem).filter_by(sessao=self.sessao).delete()
        self.session.commit()

        self.sessao = None
        self.detalhes = {"Movimentos": []}
        self.contagens = {}
        self.binds = {}
        self.labels = {}

        snackbar = ft.SnackBar(ft.Text("Sessão finalizada e removida!"), bgcolor="BLUE")
        self.page.overlay.append(snackbar)
        snackbar.open = True

        self.restart_app()
    except Exception as ex:
        logging.error(f"Erro ao finalizar sessão: {ex}")
        self.session.rollback()
