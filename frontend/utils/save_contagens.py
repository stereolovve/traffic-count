import flet as ft
import pandas as pd
import os
import re
import logging
from datetime import datetime
def save_contagens(self, e):
    try:
        contagens_dfs = {}
        for movimento in self.detalhes["Movimentos"]:
            contagens_movimento = {veiculo: count for (veiculo, mov), count in self.contagens.items() if mov == movimento}
            contagens_df = pd.DataFrame([contagens_movimento])
            contagens_df.fillna(0, inplace=True)
            contagens_dfs[movimento] = contagens_df

        detalhes_df = pd.DataFrame([self.detalhes])

        nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.detalhes['Pesquisador'])
        codigo = re.sub(r'[<>:"/\\|?*]', '', self.detalhes['Código'])

        diretorio_base = r'Z:\0Pesquisa\_0ContadorDigital\Contagens'
        
        if not os.path.exists(diretorio_base):
            diretorio_base = os.getcwd()

        diretorio_pesquisador_codigo = os.path.join(diretorio_base, nome_pesquisador, codigo)
        if not os.path.exists(diretorio_pesquisador_codigo):
            os.makedirs(diretorio_pesquisador_codigo)

        arquivo_sessao = os.path.join(diretorio_pesquisador_codigo, f'{self.sessao}.xlsx')

        try:
            existing_df = pd.read_excel(arquivo_sessao, sheet_name=None)
            for movimento in self.detalhes["Movimentos"]:
                if movimento in existing_df:
                    contagens_dfs[movimento] = pd.concat([existing_df[movimento], contagens_dfs[movimento]])
            if 'Detalhes' in existing_df:
                detalhes_df = pd.concat([existing_df['Detalhes'], detalhes_df])
        except FileNotFoundError:
            pass

        with pd.ExcelWriter(arquivo_sessao, engine='xlsxwriter') as writer:
            for movimento, df in contagens_dfs.items():
                df.to_excel(writer, sheet_name=movimento, index=False)
            detalhes_df.to_excel(writer, sheet_name='Detalhes', index=False)

        logging.info(f"Contagem salva em {arquivo_sessao}")
        snackbar = ft.SnackBar(ft.Text("Contagens salvas com sucesso!"), bgcolor="GREEN")
        self.page.overlay.append(snackbar)
        snackbar.open = True

        # Atualizando o texto do último salvamento
        self.last_save_label.value = f"Último salvamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        self.page.update()

        # Registro no histórico que a contagem foi salva
        self.salvar_historico(veiculo="", movimento="", acao="salvamento")

    except Exception as ex:
        logging.error(f"Erro ao salvar contagens: {ex}")
        snackbar = ft.SnackBar(ft.Text("Erro ao salvar contagens."), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()