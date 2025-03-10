from pynput import keyboard
from datetime import datetime
from database.models import Session, Contagem, init_db, Sessao
import flet as ft
import logging
import time
import threading


def on_key_press(self, key):
    
    if not self.contagem_ativa:
        return
    
    def _processar_tecla():
        try:
            if hasattr(key, 'name') and key.name in ['shift_r', 'caps_lock', 'up', 'down']:
                self.movimento_tabs.selected_index = (self.movimento_tabs.selected_index + 1) % len(self.movimento_tabs.tabs)
                self.page.update()
                return
            
            if hasattr(key, 'name') and key.name.startswith('f') and key.name[1:].isdigit():
                index = int(key.name[1:]) - 1
                if 0 <= index < len(self.movimento_tabs.tabs):
                    self.movimento_tabs.selected_index = index
                    self.page.update()
                return

            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):
                char = key.char
            else:
                char = str(key).strip("'")

            current_movimento = self.movimento_tabs.tabs[self.movimento_tabs.selected_index].text

            # **Ajuste aqui:** Verifica se `char` está nos binds atualizados
            if char in self.binds.values():
                veiculo = [k for k, v in self.binds.items() if v == char][0]  # Encontra a chave (veículo)
                self.increment(veiculo, current_movimento)  # 🔥 Chama a função corretamente
            else:
                pass

        except Exception as ex:
            logging.error(f"Erro ao pressionar tecla: {ex}")

    # 🚀 Processa cada tecla pressionada em uma thread separada
    threading.Thread(target=_processar_tecla, daemon=True).start()




        
def finalizar_sessao(self):
    try:
        contagens_a_remover = self.session.query(Contagem).filter_by(sessao=self.sessao).all()
        for contagem in contagens_a_remover:
            self.session.delete(contagem)

        sessao_a_remover = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_a_remover:
            self.session.delete(sessao_a_remover)

        self.session.commit()

        self.contagens.clear()
        self.binds.clear()
        self.labels.clear()
        self.sessao = None
        self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada e removida!")))
        self.page.update()

        self.restart_app()

    except Exception as ex:
        logging.error(f"Erro ao finalizar e remover sessão: {ex}")
        self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao finalizar sessão: {ex}")))
        self.session.rollback()
        self.page.update()