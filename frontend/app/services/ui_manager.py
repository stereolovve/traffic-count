import flet as ft
from datetime import timedelta
import logging


class UIManager:
    def __init__(self, contador):
        self.contador = contador
        self.page = contador.page

    def update_after_save(self, current_timeslot, last_save_time):
        """Atualiza a UI após um salvamento"""
        try:
            if 'contagem' not in self.contador.ui_components:
                return
            
            aba_contagem = self.contador.ui_components['contagem']
            
            # Atualizar labels de salvamento
            aba_contagem.update_last_save_label(last_save_time)
            aba_contagem.update_period_status()

            # Atualizar label do período
            if hasattr(aba_contagem, 'period_label'):
                periodo_inicio = current_timeslot.strftime("%H:%M")
                periodo_fim = (current_timeslot + timedelta(minutes=15)).strftime("%H:%M")
                aba_contagem.period_label.value = f"🕒 Período: {periodo_inicio} - {periodo_fim}"
                aba_contagem.period_label.update()

            # Atualizar contadores para zero
            for key in self.contador.labels:
                label_count, _ = self.contador.labels[key]
                label_count.value = "0"
                label_count.update()

        except Exception as ex:
            logging.error(f"Erro ao atualizar UI após salvamento: {ex}")

    def show_success_message(self, message):
        """Mostra mensagem de sucesso"""
        try:
            snackbar = ft.SnackBar(ft.Text(message), bgcolor="GREEN")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao mostrar mensagem de sucesso: {ex}")

    def show_error_message(self, message):
        """Mostra mensagem de erro"""
        try:
            snackbar = ft.SnackBar(ft.Text(message), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao mostrar mensagem de erro: {ex}")
