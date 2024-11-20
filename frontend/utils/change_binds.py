import flet as ft
from sqlalchemy.exc import SQLAlchemyError
from database.models import Session, Categoria

def change_binds(page, contador):
    try:
        categorias = contador.session.query(Categoria).distinct(Categoria.veiculo).all()
    except SQLAlchemyError as ex:
        logging.error(f"Erro ao carregar categorias: {ex}")
        page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao carregar categorias: {ex}"), bgcolor="RED")
        page.snack_bar.open = True
        return
    # Função para salvar o bind atualizado no banco de dados
    def salvar_bind_no_banco(veiculo, bind_atualizado):
        if bind_atualizado:
            try:
                # Atualizar o banco de dados
                categoria = contador.session.query(Categoria).filter_by(veiculo=veiculo).first()
                if categoria:
                    categoria.bind = bind_atualizado
                    contador.session.commit()
                    
                    # Atualizar o dicionário de binds do sistema
                    contador.update_binds()

                    # Atualizar a aba de contagem
                    contador.setup_aba_contagem()

                    # Exibir mensagem de sucesso
                    page.snack_bar = ft.SnackBar(ft.Text(f"Bind de '{veiculo}' atualizado com sucesso!"), bgcolor="GREEN")
                    page.snack_bar.open = True
            except SQLAlchemyError as ex:
                contador.session.rollback()
                logging.error(f"Erro ao salvar bind: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar bind: {ex}"), bgcolor="RED")
                page.snack_bar.open = True
            finally:
                page.update()
    # Função para fechar o diálogo
    def fechar_dialogo(e):
        page.dialog.open = False
        page.update()

    # Buscar todas as categorias do banco de dados vinculadas ao padrão atual
    try:
        categorias = contador.session.query(Categoria).filter_by(padrao=contador.padrao_dropdown.value).all()

        if not categorias:
            page.snack_bar = ft.SnackBar(ft.Text("Nenhuma categoria encontrada para o padrão selecionado!"), bgcolor="RED")
            page.snack_bar.open = True
            page.update()
            return
    except SQLAlchemyError as ex:
        page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao buscar categorias: {ex}"), bgcolor="RED")
        page.snack_bar.open = True
        page.update()
        return

    # Criar os campos de edição de binds
    content = ft.Column(spacing=10, scroll="adaptive")

    for categoria in categorias:
        veiculo = categoria.veiculo
        bind_field = ft.TextField(value=categoria.bind)
        salvar_button = ft.ElevatedButton(
            text="Salvar",
            on_click=lambda e, veiculo=veiculo, bind_field=bind_field: salvar_bind_no_banco(veiculo, bind_field.value)
        )

        content.controls.append(ft.Text(f"Atalho de {veiculo}"))
        content.controls.append(bind_field)
        content.controls.append(salvar_button)

    # Criar o diálogo para configuração de binds
    dialog = ft.AlertDialog(
        title=ft.Text("Configurar Atalhos"),
        content=ft.Container(content=content, width=400, height=600),  # Define uma altura fixa para suportar o scrolling
        actions=[ft.TextButton("Fechar", on_click=fechar_dialogo)]
    )

    # Atribuir e abrir o diálogo
    page.dialog = dialog
    page.dialog.open = True
    page.update()

