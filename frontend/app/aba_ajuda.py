import flet as ft

def setup_aba_ajuda(contador):
    tab = ft.Column(
        controls=[
            ft.Text("📌 Guia de uso", size=18, weight=ft.FontWeight.BOLD, color="BLUE"),
            ft.Text("Bem-vindo ao aplicativo Contador Perplan! Aqui está um guia rápido sobre cada aba:", size=14),
            ft.Divider(),
            ft.Text("🟢 Login ou cadastro: Cadastre sua conta, caso tenha uma, pode logar.", size=14),
            ft.Text("🟢 Início: Cadastre um novo ponto e configure a sessão atual. Lembre-se de escrever tudo certinho.", size=14),
            ft.Text("🟢 Contador: Onde você pode registrar suas contagens e visualizar os dados em tempo real.", size=14),
            ft.Text("🟢 Histórico: Veja os ultimos 30 registros anteriores para lembrar o que fez.", size=14),
            ft.Text("🟢 Relatório: Uma visão de como a tabela excel está.", size=14),
            ft.Text("🟢 Configurações: Personalize preferências e modifique atalhos de teclado.", size=14),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=10,
    )

    contador.tabs.tabs.append(ft.Tab(text="", content=tab, icon=ft.icons.HELP))
