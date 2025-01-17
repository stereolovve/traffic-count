import flet as ft
from datetime import datetime

class CustomDatePicker(ft.UserControl):
    def __init__(self, on_change=None, on_cancel=None, start_year=2020, end_year=2030):
        super().__init__()
        self.on_change = on_change
        self.on_cancel = on_cancel
        self.start_year = start_year
        self.end_year = end_year

        self.months = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]

        self.day_options = [ft.dropdown.Option(str(d)) for d in range(1, 32)]
        self.month_options = [ft.dropdown.Option(m) for m in self.months]
        self.year_options = [ft.dropdown.Option(str(y)) for y in range(self.start_year, self.end_year+1)]

        self.day_dropdown = ft.Dropdown(label="Dia", options=self.day_options, width=80)
        self.month_dropdown = ft.Dropdown(label="Mês", options=self.month_options, width=120)
        self.year_dropdown = ft.Dropdown(label="Ano", options=self.year_options, width=100)

        self.confirm_button = ft.ElevatedButton("Confirmar", on_click=self.confirm_date)
        self.cancel_button = ft.ElevatedButton("Cancelar", on_click=self.cancel_selection)

    def build(self):
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        self.day_dropdown,
                        self.month_dropdown,
                        self.year_dropdown
                    ]
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10,
                    controls=[
                        self.cancel_button,
                        self.confirm_button,
                    ]
                )
            ]
        )


    def confirm_date(self, e):
        # Obtém valores selecionados
        day = self.day_dropdown.value
        month = self.month_dropdown.value
        year = self.year_dropdown.value

        if not day or not month or not year:
            # Caso algum campo não tenha sido selecionado
            dlg = ft.SnackBar(ft.Text("Selecione dia, mês e ano!"), bgcolor="RED")
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
            return

        # Converte o mês do nome para número (1-12)
        month_num = self.months.index(month) + 1

        # Cria objeto datetime (assumindo que o dia é válido para o mês/ano selecionados)
        try:
            selected_date = datetime(int(year), month_num, int(day))
        except ValueError:
            # Caso a data seja inválida, por exemplo 31/02
            dlg = ft.SnackBar(ft.Text("Data inválida! Selecione valores adequados."), bgcolor="RED")
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
            return

        # Chama callback on_change, se existir
        if self.on_change:
            self.on_change(selected_date)

    def cancel_selection(self, e):
        # Chama callback on_cancel, se existir
        if self.on_cancel:
            self.on_cancel()
