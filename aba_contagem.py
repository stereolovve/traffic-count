import flet as ft

def setup_aba_contagem(self):
    tab = self.tabs.tabs[1].content
    tab.controls.clear()
    self.contagem_ativa = False

    self.toggle_button = ft.Switch(
        tooltip="Ativar contagem",
        value=False,
        on_change=self.toggle_contagem
    )

    save_button = ft.IconButton(
        icon=ft.icons.SAVE,
        icon_color="lightblue",
        tooltip="Salvar contagem",
        on_click=self.save_contagens
    )

    end_session_button = ft.IconButton(
        icon=ft.icons.STOP,
        tooltip="Finalizar sessão",
        icon_color="RED",
        on_click=self.confirmar_finalizar_sessao
    )

    reset_all_button = ft.IconButton(
        icon=ft.icons.REFRESH,
        icon_color="orange",
        tooltip="Resetar todas as contagens",
        on_click=self.confirmar_resetar_todas_contagens  # Chama o diálogo de confirmação
    )

    # Adicionando o indicador de último salvamento
    self.last_save_label = ft.Text("Último salvamento: ainda não salvo", size=12, color="gray")

    controls_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
        controls=[self.toggle_button, save_button, end_session_button, reset_all_button],
    )

    tab.controls.append(controls_row)
    tab.controls.append(self.last_save_label)  # Exibe o texto de salvamento

    # Adicionar cabeçalho dentro de cada aba de contagem
    self.movimento_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=50,
        tabs=[ft.Tab(text=movimento, content=self.criar_conteudo_movimento(movimento))
            for movimento in self.detalhes["Movimentos"]],
        expand=1,
    )

    tab.controls.append(self.movimento_tabs)

    # Cabeçalho movido para dentro da função criar_conteudo_movimento
    self.page.update()

def resetar_todas_contagens(self, e):
    try:
        current_movimento = self.movimento_tabs.tabs[self.movimento_tabs.selected_index].text
        for veiculo in [v for v, m in self.contagens.keys() if m == current_movimento]:
            self.contagens[(veiculo, current_movimento)] = 0
            self.update_labels(veiculo, current_movimento)
            self.save_to_db(veiculo, current_movimento)
        snackbar = ft.SnackBar(ft.Text(f"Contagens do movimento '{current_movimento}' foram resetadas."), bgcolor="BLUE")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

        # Salvar no histórico
        self.salvar_historico(veiculo="N/A", movimento=current_movimento, acao="reset")

    except Exception as ex:
        print(f"Erro ao resetar contagens do movimento '{current_movimento}': {ex}")
        snackbar = ft.SnackBar(ft.Text(f"Erro ao resetar contagens do movimento '{current_movimento}'."), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

def confirmar_resetar_todas_contagens(self, e):
    """Diálogo de confirmação para resetar todas as contagens"""
    def close_dialog(e):
        dialog.open = False
        self.page.update()

    def reset_and_close(e):
        dialog.open = False
        self.page.update()
        self.resetar_todas_contagens(None)  # Chama o método real de resetar as contagens

    dialog = ft.AlertDialog(
        title=ft.Text("Resetar Todas as Contagens"),
        content=ft.Text("Você tem certeza que deseja resetar todas as contagens?"),
        actions=[
            ft.TextButton("Sim", on_click=reset_and_close),
            ft.TextButton("Cancelar", on_click=close_dialog),
        ],
    )
    self.page.overlay.append(dialog)
    dialog.open = True
    self.page.update()

def criar_conteudo_movimento(self, movimento):
    content = ft.Column()

    # Adicionar o cabeçalho para cada movimento, colocando em um Row com height fixo para evitar sobreposição
    header = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Container(content=ft.Text("       Categoria", weight=ft.FontWeight.W_400, size=12), width=150, height=40),
            ft.Container(content=ft.Text("Bind", weight=ft.FontWeight.W_400, size=12), width=50, height=40),
            ft.Container(content=ft.Text("Contagem", weight=ft.FontWeight.W_400, size=12), width=80, height=40),
            ft.Container(content=ft.Text("Ações", weight=ft.FontWeight.W_400, size=12), width=50, height=40),
        ],
        height=50,  # Define uma altura fixa para evitar que ele suba e cause sobreposição
    )

    content.controls.append(header)

    categorias = [c for c in self.categorias if c.movimento == movimento]
    for categoria in categorias:
        control = self.create_category_control(categoria.veiculo, categoria.bind, movimento)
        content.controls.append(control)

    return content

def create_category_control(self, veiculo, bind, movimento):
    label_veiculo = ft.Text(f"{veiculo}", size=15, width=100)
    label_bind = ft.Text(f"({bind})", color="cyan", size=15, width=50)
    label_count = ft.Text(f"{self.contagens.get((veiculo, movimento), 0)}", size=15, width=50)
    self.labels[(veiculo, movimento)] = label_count

    # Variável para manter o campo escondido até ser necessário
    campo_visivel = False

    popup_menu = ft.PopupMenuButton(
        icon_color="teal",
        items=[
            ft.PopupMenuItem(text="Adicionar", icon=ft.icons.ADD, on_click=lambda e, v=veiculo, m=movimento: self.increment(v, m)),
            ft.PopupMenuItem(text="Remover", icon=ft.icons.REMOVE, on_click=lambda e, v=veiculo, m=movimento: self.decrement(v, m)),
            ft.PopupMenuItem(text="Editar Contagem", icon=ft.icons.EDIT, on_click=lambda e: self.abrir_edicao_contagem(veiculo, movimento)),
            ft.PopupMenuItem(text="Editar Bind", icon=ft.icons.EDIT, on_click=lambda e, v=veiculo, m=movimento: self.editar_bind(v, m))
        ]
    )

    return ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=5,
        controls=[
            ft.Container(content=label_veiculo, alignment=ft.alignment.center_left),
            ft.Container(content=label_bind, alignment=ft.alignment.center),
            ft.Container(content=label_count, alignment=ft.alignment.center_right),
            popup_menu
        ]
    )

def atualizar_borda_contagem(self):
    """Atualiza a cor da borda (fundo) da janela com base no status do contador"""
    if self.contagem_ativa:
        # Cor verde para indicar que o contador está ativo
        self.page.window.bgcolor = "green"
        self.toggle_button.bgcolor = "lightgreen"
        self.toggle_button.shadow = ft.BoxShadow(blur_radius=15, color="lightgreen")  # Efeito de brilho
        
        # Efeito pulsante usando Animation
        self.toggle_button.scale = 1.1
        self.toggle_button.animate_scale = ft.Animation(duration=500, curve=ft.AnimationCurve.BOUNCE_OUT)
    else:
        # Cor vermelha para indicar que o contador está desativado
        self.page.window.bgcolor = "red"
        self.toggle_button.bgcolor = "orange"
        self.toggle_button.shadow = ft.BoxShadow(blur_radius=15, color="orange")
        
        # Remover animação quando o contador está desligado
        self.toggle_button.scale = 1.1
        self.toggle_button.animate_scale = ft.Animation(duration=500, curve=ft.AnimationCurve.EASE_IN_OUT)
    
    self.page.update()