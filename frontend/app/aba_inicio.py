import logging

async def load_codigos(self):
    """Carrega os códigos do backend"""
    try:
        response = await async_api_request("/codigos/")
        if response and 'codigos' in response:
            self.codigo_dropdown.options = [
                ft.dropdown.Option(key=code, text=code)
                for code in response['codigos']
            ]
            self.codigo_dropdown.update()
    except Exception as e:
        logging.error(f"Erro ao carregar códigos: {e}")
        self.show_snackbar("Erro ao carregar códigos", "error")

async def load_padroes(self):
    """Carrega os padrões do backend"""
    try:
        response = await async_api_request("/padroes/")
        if response and 'padroes' in response:
            self.padrao_dropdown.options = [
                ft.dropdown.Option(key=padrao, text=padrao)
                for padrao in response['padroes']
            ]
            self.padrao_dropdown.update()
    except Exception as e:
        logging.error(f"Erro ao carregar padrões: {e}")
        self.show_snackbar("Erro ao carregar padrões", "error") 