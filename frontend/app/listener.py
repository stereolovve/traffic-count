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
            # Verificar se temos acesso aos componentes necessários
            if not hasattr(self, 'ui_components') or 'contagem' not in self.ui_components:
                return
            
            aba_contagem = self.ui_components['contagem']
            if not hasattr(aba_contagem, 'movimento_tabs') or not aba_contagem.movimento_tabs:
                return

            # Processar teclas de navegação
            if hasattr(key, 'name'):
                if key.name in ['shift_r', 'caps_lock', 'up']:
                    aba_contagem.movimento_tabs.selected_index = (
                        aba_contagem.movimento_tabs.selected_index + 1
                    ) % len(aba_contagem.movimento_tabs.tabs)
                    self.page.update()
                    return
                
                if key.name in ['down']:
                    aba_contagem.movimento_tabs.selected_index = (
                        aba_contagem.movimento_tabs.selected_index - 1
                    ) % len(aba_contagem.movimento_tabs.tabs)
                    self.page.update()
                    return
                
                if key.name.startswith('f') and key.name[1:].isdigit():
                    index = int(key.name[1:]) - 1
                    if 0 <= index < len(aba_contagem.movimento_tabs.tabs):
                        aba_contagem.movimento_tabs.selected_index = index
                        self.page.update()
                    return

            # Processar teclas normais
            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):
                char = key.char
            else:
                char = str(key).strip("'")

            movimento_atual = aba_contagem.movimento_tabs.tabs[
                aba_contagem.movimento_tabs.selected_index
            ].text

            if char in self.binds.values():
                veiculo = [k for k, v in self.binds.items() if v == char][0]
                self.increment(veiculo, movimento_atual)

        except Exception as ex:
            logging.error(f"Erro ao pressionar tecla: {ex}")

    threading.Thread(target=_processar_tecla, daemon=True).start()

        
