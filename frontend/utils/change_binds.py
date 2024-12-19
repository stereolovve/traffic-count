import flet as ft
from sqlalchemy.exc import SQLAlchemyError
from database.models import Session, Categoria, Sessao

def change_binds(page, contador):
    if hasattr(page, 'dialog') and page.dialog is not None:
        page.dialog.open = False
        page.dialog = None

    padrao_atual = contador.padrao_dropdown.value
    if not padrao_atual:
        sessao_ativa = contador.session.query(Sessao).filter_by(sessao=contador.sessao).first()
        if sessao_ativa:
            padrao_atual = sessao_ativa.padrao
        else:
            padrao_atual = None

    if not padrao_atual:
        page.snack_bar = ft.SnackBar(ft.Text("Nenhum padrão selecionado!"), bgcolor="RED")
        page.snack_bar.open = True
        page.update()
        return

    try:
        categorias = contador.session.query(Categoria).filter_by(padrao=padrao_atual).all()

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

    def salvar_bind_no_banco(veiculo, bind_atualizado):
        if bind_atualizado:
            try:
                categorias_update = contador.session.query(Categoria).filter_by(veiculo=veiculo, padrao=padrao_atual).all()
                for categoria_up in categorias_update:
                    categoria_up.bind = bind_atualizado
                contador.session.commit()
                contador.update_binds()
                contador.setup_aba_contagem()
                contador.page.update()
                page.snack_bar = ft.SnackBar(ft.Text(f"Bind de '{veiculo}' atualizado com sucesso!"), bgcolor="GREEN")
                page.snack_bar.open = True
            except SQLAlchemyError as ex:
                contador.session.rollback()
                logging.error(f"Erro ao salvar bind: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar bind: {ex}"), bgcolor="RED")
                page.snack_bar.open = True
            finally:
                page.update()

    def fechar_dialogo(e):
        page.dialog.open = False
        page.update()

    content = ft.Column(spacing=10, scroll="adaptive")

    veiculos_exibidos = set()
    for categoria in categorias:
        veiculo = categoria.veiculo
        if veiculo in veiculos_exibidos:
            continue
        veiculos_exibidos.add(veiculo)

        bind_field = ft.TextField(value=categoria.bind)
        salvar_button = ft.ElevatedButton(
            text="Salvar",
            on_click=lambda e, v=veiculo, bf=bind_field: salvar_bind_no_banco(v, bf.value)
        )

        content.controls.append(ft.Text(f"Atalho de {veiculo}", weight=ft.FontWeight.BOLD))
        content.controls.append(bind_field)
        content.controls.append(salvar_button)
        content.controls.append(ft.Divider())

    dialog = ft.AlertDialog(
        title=ft.Text(f"Configurar Binds ({padrao_atual})"),
        content=ft.Container(content=content, width=400, height=600),
        actions=[ft.TextButton("Fechar", on_click=fechar_dialogo)]
    )

    page.dialog = dialog
    page.dialog.open = True
    page.update()
