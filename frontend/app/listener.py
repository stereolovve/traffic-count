from pynput import keyboard
from datetime import datetime
from database.models import Session, init_db, Sessao
import flet as ft
import logging
import time
import threading


def on_key_press(self, key):
    from pynput.keyboard import Key, KeyCode
    # Tecla única: F12 para salvar rapidamente
    if key == Key.f12:
        try:
            self.save_contagens(None)
        except Exception as ex:
            logging.error(f"Erro ao ativar atalho salvar F12: {ex}")
        return
    # Registrar pressionamento de Ctrl
    if key in (Key.ctrl_l, Key.ctrl_r):
        if not hasattr(self, 'pressed_keys'): self.pressed_keys = set()
        self.pressed_keys.add(key)
        return

    # Bloquear outras operações se contagem não ativa
    if not self.contagem_ativa:
        return
    
    def _processar_tecla():
        try:
            if not hasattr(self, 'ui_components') or 'contagem' not in self.ui_components:
                return
            
            aba_contagem = self.ui_components['contagem']
            if not hasattr(aba_contagem, 'movimento_tabs') or not aba_contagem.movimento_tabs:
                return

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


def on_key_release(self, key):
    # Limpar estado de Ctrl
    from pynput.keyboard import Key
    try:
        if key in (Key.ctrl_l, Key.ctrl_r) and hasattr(self, 'pressed_keys'):
            self.pressed_keys.discard(key)
    except Exception as ex:
        logging.error(f"Erro no on_key_release: {ex}")
