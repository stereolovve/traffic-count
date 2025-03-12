# app/aba_contagem.py
import flet as ft
import logging
from datetime import datetime, timedelta

logging.getLogger(__name__).setLevel(logging.DEBUG)

def setup_aba_contagem(self):
    tab = self.tabs.tabs[1].content
    tab.controls.clear()
    self.contagem_ativa = False
    self.labels.clear()

    self.session_info = ft.Container(
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(f"👤 Usuário: {self.username}", size=14, weight=ft.FontWeight.W_500),
                ft.Text(f"📌 Sessão: {self.sessao if self.sessao else 'Nenhuma'}", size=14, weight=ft.FontWeight.W_500),
            ],
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        bgcolor="RED",
        border_radius=8,
    )

    self.toggle_button = ft.Switch(
        tooltip="🟢 Ativar Contagem",
        value=False,
        on_change=self.toggle_contagem
    )

    action_buttons = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
        controls=[
            self.toggle_button,
            ft.IconButton(icon=ft.icons.SAVE, icon_color="BLUE", tooltip="Salvar", on_click=self.save_contagens),
            ft.IconButton(icon=ft.icons.CLOSE, icon_color="RED", tooltip="Finalizar", on_click=self.confirmar_finalizar_sessao),
            ft.IconButton(icon=ft.icons.RESTART_ALT, icon_color="ORANGE", tooltip="Resetar", on_click=self.confirm_reset_all_countings),
            ft.IconButton(icon=ft.icons.INFO, icon_color="PURPLE", tooltip="Observação", on_click=self.abrir_dialogo_observacao),
        ]
    )

    if not hasattr(self, "last_save_time") or self.last_save_time is None:
        self.last_save_time = datetime.now()
    
    self.last_save_label = ft.Text(
        value=f"⏳ Último salvamento: {self.last_save_time.strftime('%H:%M:%S')}",
        size=14, weight=ft.FontWeight.W_500
    )

    if not hasattr(self, "current_timeslot") or self.current_timeslot is None:
        self.current_timeslot = datetime.strptime(self.details["HorarioInicio"], "%H:%M") if "HorarioInicio" in self.details else datetime.now().replace(second=0, microsecond=0)

    periodo_inicio = self.current_timeslot.strftime("%H:%M")
    periodo_fim = (self.current_timeslot + timedelta(minutes=15)).strftime("%H:%M")
    
    self.period_label = ft.Text(
        value=f"🕒 Período: {periodo_inicio} - {periodo_fim}",
        size=14, weight=ft.FontWeight.W_500
    )

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
        alignment=ft.alignment.center
    )

    movimentos = self.details.get("Movimentos", [])
    if not movimentos:
        logging.warning("[WARNING] Nenhum movimento encontrado em self.details['Movimentos']")
        tab.controls.append(ft.Text("⚠ Nenhum movimento disponível", color="red"))
    else:
        self.movimento_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=0,
            tabs=[ft.Tab(text=mov, content=self.create_moviment_content(mov)) for mov in movimentos],
            expand=1,
        )
        tab.controls.extend([
            self.session_info, 
            action_buttons, 
            self.status_container, 
            self.movimento_tabs
        ])

    tab.visible = True
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


def reset_all_countings(self, e):
    try:
        current_movimento = self.movimento_tabs.tabs[self.movimento_tabs.selected_index].text
        for veiculo in [v for v, m in self.contagens.keys() if m == current_movimento]:
            self.contagens[(veiculo, current_movimento)] = 0
            self.update_labels(veiculo, current_movimento)
            self.save_to_db(veiculo, current_movimento)
            self.salvar_historico(veiculo, current_movimento, "reset")

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
