import flet as ft
import json
from sqlalchemy.exc import SQLAlchemyError
from database.models import Session, Categoria

def change_binds(page, contador):
    # Carregar o arquivo JSON com as binds
    try:
        with open('padrao.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = []

    # Função para salvar o bind atualizado no banco de dados
    def salvar_bind_no_banco(veiculo, bind_atualizado):
        if bind_atualizado:
            contador.update_bind(veiculo, bind_atualizado, movimento="")  # Utilize a função existente para atualizar o banco de dados

            # Atualizando o arquivo padrao.json
            try:
                with open('padrao.json', 'r') as f:
                    config = json.load(f)

                for c in config:
                    if c['veiculo'] == veiculo:
                        c['bind'] = bind_atualizado  # Atualiza o bind no arquivo JSON

                with open('padrao.json', 'w') as f:
                    json.dump(config, f, indent=4)

                page.snack_bar = ft.SnackBar(ft.Text(f"Bind de {veiculo} atualizado com sucesso!"), bgcolor="GREEN")
                page.snack_bar.open = True

            except FileNotFoundError:
                page.snack_bar = ft.SnackBar(ft.Text("Arquivo padrao.json não encontrado!"), bgcolor="RED")
                page.snack_bar.open = True

            page.update()

    # Função para fechar o diálogo
    def fechar_dialogo(e):
        page.dialog.open = False
        page.update()

    # Gerar os campos de veículos e binds dentro do conteúdo do diálogo
    content = ft.ListView(expand=True, spacing=10)  # ListView para suportar scrolling

    for c in config:
        veiculo = c['veiculo']
        bind_field = ft.TextField(value=c['bind'])
        salvar_button = ft.ElevatedButton(text="Salvar", on_click=lambda e, veiculo=veiculo, bind_field=bind_field: salvar_bind_no_banco(veiculo, bind_field.value))
        
        content.controls.append(ft.Text(f"Veículo: {veiculo}"))
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