# app/aba_contagem.py
import flet as ft
import logging
from datetime import datetime, timedelta
from pynput import keyboard
import asyncio

logging.getLogger(__name__).setLevel(logging.DEBUG)

class AbaContagem(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        
        # Usar a página do contador como referência
        if hasattr(contador, 'page') and contador.page is not None:
            self.page = contador.page
        else:
            logging.warning("⚠️ Contador não possui um page válido - isso pode causar erros!")
            self.page = None
        
        self.scroll = ft.ScrollMode.AUTO
        self.spacing = 10
        
        # Atributos que serão inicializados no setup_ui
        self.session_info = None
        self.toggle_button = None
        self.last_save_label = None
        self.period_label = None
        self.status_container = None
        self.movimento_tabs = None
        self.listener_switch = None
        
        # Inicializar a UI
        self.setup_ui()

    def setup_ui(self):
        try:
            self.controls.clear()
            self.contador.contagem_ativa = False
            self.contador.labels.clear()

            # Container principal com altura e largura mínimas
            main_container = ft.Container(
                content=ft.Column(
                    controls=[],
                    spacing=10,
                    expand=True,
                ),
                expand=True,
                width=float('inf'),  # Largura total
            )

            # Informações da sessão
            self.session_info = ft.Container(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"👤 Usuário: {self.contador.username}", size=14, weight=ft.FontWeight.W_500),
                        ft.Text(f"📌 Sessão: {self.contador.sessao if self.contador.sessao else 'Nenhuma'}", 
                               size=14, weight=ft.FontWeight.W_500),
                    ],
                ),
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                bgcolor="RED",
                border_radius=8,
                width=float('inf'),  # Força largura total
            )

            self.toggle_button = ft.Switch(
                tooltip="🟢 Ativar Contagem",
                value=False,
                on_change=self.toggle_contagem
            )

            # Botões de ação com altura fixa
            action_buttons = ft.Container(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        self.toggle_button,
                        ft.IconButton(icon=ft.icons.SAVE, icon_color="BLUE", tooltip="Salvar", 
                                    on_click=self.contador.save_contagens),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_color="RED", tooltip="Finalizar", 
                                    on_click=self.contador.show_dialog_end_session),
                        ft.IconButton(icon=ft.icons.RESTART_ALT, icon_color="ORANGE", tooltip="Resetar", 
                                    on_click=self.confirm_reset_all_countings),
                        ft.IconButton(icon=ft.icons.INFO, icon_color="PURPLE", tooltip="Observação", 
                                    on_click=self.contador.abrir_dialogo_observacao),
                    ]
                ),
                height=50  # Altura fixa para os botões
            )

            # Configurar labels de tempo
            if not hasattr(self.contador, "last_save_time") or self.contador.last_save_time is None:
                # Usar o horário inicial da sessão como referência para o último salvamento
                if "HorarioInicio" in self.contador.details:
                    self.contador.last_save_time = datetime.strptime(
                        self.contador.details["HorarioInicio"], 
                        "%H:%M"
                    )
                else:
                    self.contador.last_save_time = datetime.now()
            
            self.last_save_label = ft.Text(
                value=f"⏳ Último salvamento: {self.contador.last_save_time.strftime('%H:%M:%S')}",
                size=14, weight=ft.FontWeight.W_500
            )

            # Configurar o período atual
            if not hasattr(self.contador, "current_timeslot") or self.contador.current_timeslot is None:
                if "current_timeslot" in self.contador.details:
                    self.contador.current_timeslot = datetime.strptime(
                        self.contador.details["current_timeslot"], 
                        "%H:%M"
                    )
                elif "HorarioInicio" in self.contador.details:
                    self.contador.current_timeslot = datetime.strptime(
                        self.contador.details["HorarioInicio"], 
                        "%H:%M"
                    )
                else:
                    self.contador.current_timeslot = datetime.now().replace(second=0, microsecond=0)

            periodo_inicio = self.contador.current_timeslot.strftime("%H:%M")
            periodo_fim = (self.contador.current_timeslot + timedelta(minutes=15)).strftime("%H:%M")
            
            self.period_label = ft.Text(
                value=f"🕒 Período: {periodo_inicio} - {periodo_fim}",
                size=14, weight=ft.FontWeight.W_500
            )

            # Container de status com altura fixa
            self.status_container = ft.Container(
                content=ft.Row(
                    controls=[self.last_save_label, self.period_label],
                    spacing=15,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                bgcolor="RED",
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                border_radius=8,
                margin=ft.margin.only(top=10, bottom=10),
                height=40,  # Altura fixa para o status
                width=float('inf')  # Largura total
            )

            # Tabs de movimentos
            movimentos = self.contador.details.get("Movimentos", [])
            if movimentos and self.contador.categorias:
                self.movimento_tabs = ft.Tabs(
                    selected_index=0,
                    animation_duration=0,
                    tabs=[
                        ft.Tab(
                            text=mov,
                            content=ft.Container(
                                content=self.create_moviment_content(mov),
                                padding=10,
                                expand=True,
                            )
                        ) for mov in movimentos
                    ],
                    expand=True
                )
                
                # Adicionar todos os elementos ao container principal
                main_container.content.controls.extend([
                    self.session_info,
                    action_buttons,
                    self.status_container,
                    self.movimento_tabs
                ])
            else:
                # Mensagem de erro/aviso se não houver movimentos ou categorias
                main_container.content.controls.append(
                    ft.Text("⚠ Aguardando carregamento das categorias...", color="yellow")
                )

            # Adicionar o container principal à aba
            self.controls.append(main_container)
            self.visible = True

            # Atualizar a página
            if self.page:
                self.page.update()
            elif self.contador.page:
                self.contador.page.update()

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao configurar UI da aba contagem: {ex}")
            raise

    def toggle_listener(self, e):
        if self.listener_switch.value:
            self.start_listener()
            self.listener_switch.label = "🎧 Listener Ativado"
            logging.info("✅ Listener ativado")
        else:
            self.stop_listener()
            self.listener_switch.label = "🚫 Listener Desativado"
            logging.info("❌ Listener desativado")

        self.listener_switch.update()
        self.page.update()

    def reset_all_countings(self, e):
        try:
            current_movimento = self.movimento_tabs.tabs[self.movimento_tabs.selected_index].text
            for veiculo in [v for v, m in self.contador.contagens.keys() if m == current_movimento]:
                # Primeiro encontrar a categoria correta
                categoria = next(
                    (c for c in self.contador.categorias 
                     if c.veiculo == veiculo and c.movimento == current_movimento), 
                    None
                )
                
                if categoria:
                    self.contador.contagens[(veiculo, current_movimento)] = 0
                    self.update_labels(veiculo, current_movimento)
                    self.contador.save_to_db(veiculo, current_movimento)
                    # Passar o ID da categoria em vez do veículo
                    self.contador.salvar_historico(categoria.id, current_movimento, "reset")
                else:
                    logging.warning(f"Categoria não encontrada para {veiculo} - {current_movimento}")

            snackbar = ft.SnackBar(
                ft.Text(f"✅ Contagens do movimento '{current_movimento}' foram resetadas."),
                bgcolor="BLUE"
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

            logging.info(f"[INFO] Contagens resetadas para movimento '{current_movimento}'")

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao resetar contagens do movimento '{current_movimento}': {ex}")
            snackbar = ft.SnackBar(
                ft.Text(f"❌ Erro ao resetar contagens do movimento '{current_movimento}'."), bgcolor="RED"
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

    def confirm_reset_all_countings(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def confirm_reset(e):
            dialog.open = False
            self.page.update()
            self.reset_all_countings(e)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Reset"),
            content=ft.Text("Tem certeza de que deseja resetar todas as contagens? Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Confirmar", on_click=confirm_reset),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def create_moviment_content(self, movimento):
        logging.debug(f"[DEBUG] Criando conteúdo para o movimento: {movimento}")

        content = ft.Column()
        
        # Verificar se temos categorias no contador
        if not self.contador.categorias:
            logging.warning("[WARNING] Nenhuma categoria disponível no contador")
            content.controls.append(ft.Text("⚠ Aguardando carregamento das categorias...", color="yellow"))
            return content
        
        categorias = [c for c in self.contador.categorias if movimento.strip().upper() == c.movimento.strip().upper()]
        
        logging.debug(f"[DEBUG] Categorias encontradas para {movimento}: {[(c.veiculo, c.movimento) for c in categorias]}")

        if not categorias:
            logging.warning(f"[WARNING] Nenhuma categoria encontrada para movimento {movimento}")
            content.controls.append(ft.Text(f"⚠ Nenhuma categoria encontrada para {movimento}", color="red"))
        else:
            for categoria in categorias:
                veiculo = categoria.veiculo
                bind = self.contador.binds.get(veiculo, "N/A")
                control = self.create_category_control(veiculo, bind, movimento)
                content.controls.append(control)

        return content

    def create_category_control(self, veiculo, bind, movimento):
        # Simplificar - usar sempre o valor atual dos binds do contador
        bind = self.contador.binds.get(veiculo, "N/A")
        
        # Encontrar a categoria para ter acesso ao ID
        categoria = next(
            (c for c in self.contador.categorias 
             if c.veiculo == veiculo and c.movimento == movimento),
            None
        )
        
        if not categoria:
            logging.warning(f"Categoria não encontrada para {veiculo} - {movimento}")
            return None

        label_veiculo = ft.Text(f"{veiculo}", size=15, width=100)
        
        # Exibir o bind real ou um texto informativo
        label_bind = ft.Text(
            f"({bind})" if bind != "N/A" else "(Sem bind)", 
            color="cyan" if bind != "N/A" else "red", 
            size=15, 
            width=50
        )
        
        label_count = ft.Text(f"{self.contador.contagens.get((veiculo, movimento), 0)}", size=15, width=50)

        row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=5,
            controls=[
                ft.Container(content=label_veiculo, alignment=ft.alignment.center_left),
                ft.Container(content=label_bind, alignment=ft.alignment.center),
                ft.Container(content=label_count, alignment=ft.alignment.center_right),
                ft.PopupMenuButton(
                    icon_color="teal",
                    items=[
                        ft.PopupMenuItem(
                            text="Adicionar", 
                            icon=ft.icons.ADD, 
                            on_click=lambda e: self.contador.increment(veiculo, movimento)
                        ),
                        ft.PopupMenuItem(
                            text="Remover", 
                            icon=ft.icons.REMOVE, 
                            on_click=lambda e: self.contador.decrement(veiculo, movimento)
                        ),
                        ft.PopupMenuItem(
                            text="Editar Contagem", 
                            icon=ft.icons.EDIT, 
                            on_click=lambda e: self.contador.abrir_edicao_contagem(veiculo, movimento)
                        )
                    ]
                )
            ]
        )

        self.contador.labels[(veiculo, movimento)] = [label_count, label_bind]

        return row

    def toggle_contagem(self, e):
        if not hasattr(self, "toggle_button"):
            logging.error("[ERROR] toggle_button não foi inicializado.")
            return

        self.contador.contagem_ativa = self.toggle_button.value 

        try:
            if self.contador.contagem_ativa:
                logging.info("✅ Contagem ativada!")  
                self.start_listener()
            else:
                logging.info("❌ Contagem desativada!")  
                self.stop_listener()

            self.update_session_info_color()
            self.update_status_container_color()
            self.toggle_button.update()
            page = self._get_page()
            if page:
                page.update()
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao alternar contagem: {ex}")

    def update_session_info_color(self):
        if self.contador.contagem_ativa:
            self.session_info.bgcolor = "GREEN"
        else:
            self.session_info.bgcolor = "RED"
        self.session_info.update()
        self.page.update()

    def update_status_container_color(self):
        if self.contador.contagem_ativa:
            self.status_container.bgcolor = "GREEN"
        else:
            self.status_container.bgcolor = "RED"
        self.status_container.update()
        self.page.update()

    def update_current_tab(self):
        current_tab = self.movimento_tabs.tabs[self.movimento_tabs.selected_index]
        current_tab.content.update()
        self.page.update()

    def toggle_listener(self, e):
        if self.listener_switch.value:
            self.start_listener()
            self.listener_switch.label = "🎧 Listener Ativado"
            logging.info("✅ Listener ativado")
        else:
            self.stop_listener()
            self.listener_switch.label = "🚫 Listener Desativado"
            logging.info("❌ Listener desativado")

        self.listener_switch.update()
        self.page.update()

    def start_listener(self):
        if not hasattr(self.contador, "pressed_keys"):
            self.contador.pressed_keys = set()

        if self.contador.listener is None:
            self.contador.listener = keyboard.Listener(
                on_press=self.contador.on_key_press, 
                on_release=self.contador.on_key_release
            )
            self.contador.listener.start()

    def stop_listener(self):
        if self.contador.listener is not None:
            self.contador.listener.stop()
            self.contador.listener = None
            self.contador.pressed_keys.clear()

    def update_labels(self, veiculo, movimento):
        key = (veiculo, movimento)
        if key in self.contador.labels:
            label_count, label_bind = self.contador.labels[key]
            label_count.value = str(self.contador.contagens.get(key, 0))
            label_count.update()
        else:
            logging.warning(f"[WARNING] Label não encontrada para {key}. Aguardando criação.")

    def _get_page(self):
        """Retorna uma página válida, seja a própria ou a do contador"""
        if hasattr(self, 'page') and self.page is not None:
            return self.page
        elif hasattr(self.contador, 'page') and self.contador.page is not None:
            return self.contador.page
        else:
            logging.error("❌ Nenhuma página válida encontrada!")
            return None