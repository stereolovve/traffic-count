import winsound
import sys

# Teste simples com beep do sistema
print("Tocando beep do sistema...")
winsound.Beep(800, 500)  # Frequency 800Hz, Duration 500ms

# Teste com arquivo de som
sound_file = r"C:\Windows\Media\notify.wav"
try:
    print(f"Tentando tocar: {sound_file}")
    winsound.PlaySound(sound_file, winsound.SND_FILENAME)
    print("Som tocado com sucesso!")
except Exception as e:
    print(f"Erro ao tocar som: {e}")