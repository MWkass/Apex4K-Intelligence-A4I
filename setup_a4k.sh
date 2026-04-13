#!/bin/bash
# setup_a4k.sh - Instalador Automatizado Apex4K

INSTALL_DIR="$HOME/.a4k_system"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "--- Instalando Apex4K Intelligence (A4I) ---"

# 1. Baixa o binário (Substitua o link pelo seu link do GitHub Release)
# Exemplo: curl -L -o a4k "https://github.com/seu-user/repo-privado/releases/download/v1.0/a4k"
curl -L -o a4k "https://github.com/MWkass/Apex4K-Intelligence-A4I/releases/download/v1.0.0/a4k"
chmod +x a4k

# 2. Instala dependências de runtime (Se não existirem)
if ! command -v mpv &> /dev/null; then
    echo "Instalando MPV (Engine Gráfica)..."
    sudo apt update && sudo apt install -y mpv
fi

# 3. Garante que o Playwright funcione (instala apenas o navegador necessário)
./a4k --install-playwright # (Veja nota abaixo sobre como adicionar isso no main.py)

# 4. Cria o atalho no sistema para o usuário rodar de qualquer lugar
sudo ln -sf "$INSTALL_DIR/a4k" /usr/local/bin/a4k

echo "Pronto! Agora é só digitar 'a4k' no terminal."