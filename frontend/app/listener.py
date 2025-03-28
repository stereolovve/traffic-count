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
            if hasattr(key, 'name') and key.name in ['shift_r', 'caps_lock', 'up']:
                self.movimento_tabs.selected_index = (self.movimento_tabs.selected_index + 1) % len(self.movimento_tabs.tabs)
                self.page.update()
                return
            
            if hasattr(key, 'name') and key.name in ['down']:
                self.movimento_tabs.selected_index = (self.movimento_tabs.selected_index - 1) % len(self.movimento_tabs.tabs)
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

            if char in self.binds.values():
                veiculo = [k for k, v in self.binds.items() if v == char][0]
                self.increment(veiculo, current_movimento)  
            else:
                pass

        except Exception as ex:
            logging.error(f"Erro ao pressionar tecla: {ex}")

    threading.Thread(target=_processar_tecla, daemon=True).start()

        
