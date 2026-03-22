import os
import sys
import subprocess

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=" * 60)
    print(" 🎮 CryoGuard Anti-Cheat — Setup Wizard")
    print("=" * 60)
    print(" Proteja seu servidor de jogos contra movimentações impossíveis!\n")

def run():
    print_header()
    
    api_key = input(" 🔑 API Key do seu Servidor? (Cole aqui): ").strip()
    if not api_key:
        api_key = "DEMO_KEY_GAMESERVER"
    
    print("\n")
    server = input(" 🌐 Servidor Cryo [Padrão: api.cryo-corona.com:50505]: ").strip()
    if not server:
        server = "api.cryo-corona.com:50505"
        
    print("\n")
    print(" 🎚️  Limite de Punição (Surpresa)")
    threshold = input(" [0.80 Rígido | 0.85 Padrão | 0.90 Tolerante]: ").strip()
    if not threshold:
        threshold = "0.85"
        
    print("\n ⚙️  Gerando configurações...")
    with open(".env", "w") as f:
        f.write(f"CRYO_SERVER={server}\n")
        f.write(f"CRYO_API_KEY={api_key}\n")
        f.write(f"CRYOGUARD_THRESHOLD={threshold}\n")
    print(" [+] Arquivo .env criado.")
    
    print("\n 📦 Instalando dependências...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except:
        pass
        
    print("\n 🎉 Sucesso! Rode: python cryoguard.py para uma demonstração.\n")
    input(" Pressione Enter para sair...")

if __name__ == "__main__":
    run()
