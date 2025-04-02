# app/aba_contagem.py
import flet as ft
import logging
from datetime import datetime, timedelta
from pynput import keyboard
import asyncio
from database.models import Contagem, Categoria, Historico

logging.getLogger(__name__).setLevel(logging.DEBUG)

class AbaContagem(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        
        if hasattr(contador, 'page') and contador.page is not None:
            self.page = contador.page
        else:
            logging.warning("⚠️ Contador não possui um page válido - isso pode causar erros!")
            self.page = None
        
        
        self.session_info = None
        self.toggle_button = None
        self.last_save_label = None
        self.period_label = None
        self.status_container = None
        self.movimento_tabs = None
        self.listener_switch = None
        
        self.setup_ui()

    def setup_ui(self):
        try:
            self.controls.clear()
            self.contador.contagem_ativa = False
            self.contador.labels.clear()

            # Criar um ScrollableColumn para conter todo o conteúdo
            main_content = ft.Column(
                controls=[],
            )

            # Informações da sessão (fixo no topo)
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
                width=float('inf'),
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
                                    on_click=self.contador.session_manager.show_dialog_end_session),
                        ft.IconButton(icon=ft.icons.RESTART_ALT, icon_color="ORANGE", tooltip="Resetar", 
                                    on_click=lambda _: self.show_reset_dialog()),
                        ft.IconButton(icon=ft.icons.INFO, icon_color="PURPLE", tooltip="Observação", 
                                    on_click=self.abrir_dialogo_observacao),
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
                            )
                        ) for mov in movimentos
                    ]                
                    )
                
                # Adicionar todos os elementos ao main_content
                main_content.controls.extend([
                    self.session_info,
                    action_buttons,
                    self.status_container,
                    self.movimento_tabs
                ])
            else:
                main_content.controls.append(
                    ft.Text("⚠ Aguardando carregamento das categorias...", color="yellow")
                )

            # Criar um container principal que permite scroll
            main_container = ft.Container(
                content=ft.Column(
                    controls=[main_content],
                ),
                padding=10,
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

    def show_reset_dialog(self):
        def close_dialog(e):
            dialog.open = False
            self.contador.page.update()

        def confirm_reset(e):
            dialog.open = False
            self.contador.page.update()
            current_tab = self.movimento_tabs.tabs[self.movimento_tabs.selected_index]
            movimento = current_tab.text
            
            self.reset_all_countings(movimento)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Reset"),
            content=ft.Text("Tem certeza de que deseja resetar todas as contagens desta aba? Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Confirmar", on_click=confirm_reset),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.contador.page.overlay.append(dialog)
        dialog.open = True
        self.contador.page.update()

    def reset_all_countings(self, movimento):
        try:
            logging.info(f"Resetando contagens para o movimento: {movimento}")
            
            with self.contador.session_lock:
                self.contador.session.query(Contagem).filter_by(
                    sessao=self.contador.sessao,
                    movimento=movimento
                ).delete()
                self.contador.session.commit()

            for key in list(self.contador.contagens.keys()):
                if key[1] == movimento:
                    self.contador.contagens[key] = 0
                    if key in self.contador.labels:
                        label_count, _ = self.contador.labels[key]
                        label_count.value = "0"
                        label_count.update()

            self.contador.page.update()
            
            snackbar = ft.SnackBar(
                content=ft.Text(f"Contagens do movimento {movimento} foram resetadas com sucesso!"),
                bgcolor="green"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True
            self.contador.page.update()
            
            self.contador.history_manager.salvar_historico(None, movimento, "reset")

            logging.info(f"✅ Contagens do movimento {movimento} resetadas com sucesso!")

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao resetar contagens do movimento '{movimento}': {ex}")
            snackbar = ft.SnackBar(
                content=ft.Text(f"Erro ao resetar contagens: {str(ex)}"),
                bgcolor="red"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True
            self.contador.page.update()

    def create_moviment_content(self, movimento):
        content = ft.Column(
            spacing=10,
        )
        
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
        bind = self.contador.binds.get(veiculo, "N/A")
        
        categoria = next(
            (c for c in self.contador.categorias 
             if c.veiculo == veiculo and c.movimento == movimento),
            None
        )
        
        if not categoria:
            logging.warning(f"Categoria não encontrada para {veiculo} - {movimento}")
            return None

        label_veiculo = ft.Text(f"{veiculo}", size=15, width=100)
        
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
                            on_click=lambda e: self.abrir_edicao_contagem(veiculo, movimento)
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
        if hasattr(self, 'page') and self.page is not None:
            return self.page
        elif hasattr(self.contador, 'page') and self.contador.page is not None:
            return self.contador.page
        else:
            logging.error("❌ Nenhuma página válida encontrada!")
            return None

    def abrir_dialogo_observacao(self, e):
        def on_confirm(ev):
            self.contador.period_observacao = textfield.value
            dialog.open = False
            self.contador.page.update()

            snackbar = ft.SnackBar(ft.Text("✅ Observação salva!"), bgcolor="PURPLE")
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True
            self.contador.page.update()

        textfield = ft.TextField(label="Observação do período", multiline=True, width=300)
        dialog = ft.AlertDialog(
            title=ft.Text("Inserir Observação"),
            content=textfield,
            actions=[
                ft.TextButton("Confirmar", on_click=on_confirm),
                ft.TextButton("Cancelar", on_click=lambda _: self.contador.close_dialog(dialog)),
            ],
            on_dismiss=lambda _: self.contador.close_dialog(dialog),
        )

        self.contador.page.overlay.append(dialog)
        dialog.open = True
        self.contador.page.update()

    def update_last_save_label(self, now=None):
        """Atualiza o label de último salvamento"""
        if not self.last_save_label:
            return
            
        timestamp = now if now else (
            self.contador.last_save_time 
            if hasattr(self.contador, "last_save_time") 
            else datetime.now()
        )
        self.last_save_label.value = f"⏳ Último salvamento: {timestamp.strftime('%H:%M:%S')}"
        self.last_save_label.update()

    def update_period_status(self):
        """Atualiza o label de período"""
        if not self.period_label:
            return
            
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
        self.period_label.value = f"🕒 Período: {periodo_inicio} - {periodo_fim}"
        self.period_label.update()

    def abrir_edicao_contagem(self, veiculo, movimento):
        self.contagem_ativa = False
        self.page.update()

        def on_submit(e):
            try:
                nova_contagem = int(input_contagem.value)
                self.contador.contagens[(veiculo, movimento)] = nova_contagem
                self.update_labels(veiculo, movimento)
                self.contador.save_to_db(veiculo, movimento)
                
                categoria = self.contador.session.query(Categoria).filter_by(
                    padrao=self.contador.ui_components['inicio'].padrao_dropdown.value,
                    veiculo=veiculo,
                    movimento=movimento
                ).first()
                
                self.contador.history_manager.salvar_historico(categoria.id if categoria else None, movimento, "edicao manual")
                
                snackbar = ft.SnackBar(
                    ft.Text(f"Contagem de '{veiculo}' no movimento '{movimento}' foi atualizada para {nova_contagem}."),
                    bgcolor="BLUE"
                )
                self.page.overlay.append(snackbar)
                snackbar.open = True
                dialog.open = False
                self.contagem_ativa = True
                self.page.update()

            except ValueError:
                logging.error("[ERROR] Valor de contagem inválido.")

        input_contagem = ft.TextField(
            label="Nova Contagem",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=on_submit
        )
        dialog = ft.AlertDialog(
            title=ft.Text(f"Editar Contagem: {veiculo}"),
            content=input_contagem,
            actions=[ft.TextButton("Salvar", on_click=on_submit)],
            on_dismiss=lambda e: None,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()