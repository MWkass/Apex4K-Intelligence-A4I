# 🎭 Apex4K Intelligence (A4I)

O **Apex4K Intelligence** é um sistema completo e autônomo baseado em terminal (TUI) projetado para buscar, extrair e reproduzir animes com altíssima qualidade. Ele integra técnicas avançadas de Web Scraping, Inteligência Artificial e Processamento Gráfico em tempo real.

---

## 🚀 Arquitetura e Recursos Principais

- 🧠 **Self-Healing via IA (Google Gemini):** Caso a estrutura HTML dos provedores de animes mude e quebre o scraper, a IA lê o código fonte, entende o novo layout do site e propõe o reparo automaticamente.
- ⚡ **Governador Dinâmico de GPU:** O sistema se comunica com o player via Sockets IPC em tempo real. Se a sua GPU começar a gargalar ou perder frames (Frame Drops), a IA rebaixa os *Shaders* para um modo mais leve instantaneamente.
- 🎥 **Upscaling Neural (Anime4K):** Injeção nativa de shaders na engine do MPV via Vulkan, otimizando o visual para telas grandes sem a necessidade de baixar arquivos imensos.
- 🕵️ **Extração de Vídeo via Playwright:** Ignora bloqueios de Cloudflare e rastreia rotas de rede para extrair a URL HLS/MP4 pura de forma invisível no background.
- 💾 **Gestão de Estado Segura:** Salva seu histórico de onde parou em cada anime e guarda credenciais em um cofre local de forma invisível.

---

## ⚙️ Pré-requisitos

A engine de vídeo nativa requer que o sistema operacional possua o **MPV** instalado. O restante (Python, bibliotecas e navegadores ocultos) é empacotado pelo PyInstaller.

```bash
# Sistemas baseados em Debian/Ubuntu
sudo apt update && sudo apt install -y mpv
```

---

## 📦 Instalação Automatizada

Para os usuários finais, a distribuição ocorre através de um script automatizado que baixa o binário pré-compilado, instala as dependências do SO e configura o link de terminal.

1. Baixe o script de instalação oficial:
```bash
curl -L -O https://raw.githubusercontent.com/SEU_USUARIO/apex4k_intelligence/main/setup_a4k.sh
```

2. Dê permissão de execução e instale:
```bash
chmod +x setup_a4k.sh
./setup_a4k.sh
```

3. Na primeira execução, o sistema fará o download da engine headless do Chromium (Playwright).

---

## 🎮 Uso

Abra qualquer terminal e digite:
```bash
a4k
```

### Comandos do Player (Durante a exibição):
- `S`: Pula automaticamente 90 segundos (Abertura).
- `Q`: Fecha o vídeo e retorna ao menu principal.
- `CTRL+1 / 2 / 3`: Força os níveis Leve, Balanceado e Extremo da rede neural de upscaling Anime4K.
- `CTRL+0`: Desativa os shaders.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.12+
- **Scraping & Automação:** `cloudscraper`, `BeautifulSoup4`, `Playwright`
- **Inteligência Artificial:** `google-genai`, `pydantic`
- **Terminal UI:** `InquirerPy`
- **Player Gráfico:** `MPV` (via IPC Socket)

---

## ⚠️ Observações de Desenvolvimento

Para construir o executável por conta própria:

```bash
pyinstaller --noconfirm --onefile --clean \
  --name "a4k" \
  --hidden-import "scrapers.animefire" \
  --hidden-import "scrapers.animesdigital" \
  --add-data "shaders:shaders" \
  main.py
```