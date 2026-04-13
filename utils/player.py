import subprocess
import sys
import os
import socket
import json
import threading
import time

BANNER = r"""
  █████╗ ██████╗ ███████╗██╗  ██╗██╗  ██╗██╗  ██╗
 ██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██║  ██║██║ ██╔╝
 ███████║██████╔╝█████╗   ╚███╔╝ ███████║█████╔╝ 
 ██╔══██║██╔═══╝ ██╔══╝   ██╔██╗ ╚════██║██╔═██╗ 
 ██║  ██║██║     ███████╗██╔╝ ██╗     ██║██║  ██╗
 ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝     ╚═╝╚═╝  ╚═╝
         [ INTELLIGENCE SYSTEM - A4I ]
"""

def send_mpv_cmd(socket_path: str, cmd_dict: dict):
    """Envia comandos JSON via IPC Socket para o MPV em tempo real."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(socket_path)
            s.sendall((json.dumps(cmd_dict) + '\n').encode('utf-8'))
            data = s.recv(1024)
            return json.loads(data.decode('utf-8').strip())
    except Exception:
        return None

def assistir_episodio(url_video: str, titulo_anime: str, nome_episodio: str) -> None:
    print("\033c", end="")
    print(f"\033[36m{BANNER}\033[0m")
    print("  Monitorando GPU via IPC: ATIVADO")
    print("  Comandos de Teclado no Player (Overrides Manuais):")
    print("  [S] Avançar Abertura (90s)")
    print("  [Q] Fechar Vídeo")
    print("  [CTRL+0] Desativar Anime4K (Original)")
    print("  [CTRL+1] Forçar Modo LEVE (S)")
    print("  [CTRL+2] Forçar Modo BALANCEADO (M)")
    print("  [CTRL+3] Forçar Modo EXTREMO (VL)\n")
    
    # Arquitetura de Caminhos PyInstaller: Assets Embutidos vs Dados Persistentes
    if getattr(sys, 'frozen', False):
        diretorio_raiz = os.path.dirname(sys.executable)
        # Extrai os shaders da memória embutida para a pasta temporária do runtime
        pasta_shaders = os.path.join(sys._MEIPASS, "shaders")
    else:
        diretorio_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        pasta_shaders = os.path.join(diretorio_raiz, "shaders")
        
    arquivo_log = os.path.join(diretorio_raiz, "debug.log")
    arquivo_input = os.path.join(diretorio_raiz, "input_anime.conf")
    arquivo_capitulos = os.path.join(diretorio_raiz, "capitulos.txt")
    socket_ipc = os.path.join(diretorio_raiz, "mpv_ipc.sock")
    
    if os.path.exists(socket_ipc):
        try: os.remove(socket_ipc)
        except: pass
        
    # Montagem do Título Customizado
    titulo_janela = f"{titulo_anime} - {nome_episodio}"

    # 1. Geração Dinâmica de Capítulos (OGM Format)
    # Define marcadores visuais na barra do MPV. Abertura sempre ocupa os primeiros 1m30s.
    with open(arquivo_capitulos, 'w', encoding='utf-8') as f:
        f.write("CHAPTER01=00:00:00.000\n")
        f.write("CHAPTER01NAME=Abertura (Padrão 90s)\n")
        f.write("CHAPTER02=00:01:30.000\n")
        f.write("CHAPTER02NAME=Episódio\n")
        f.write("CHAPTER03=00:22:00.000\n") # Estimativa de Encerramento em animes de 24min
        f.write("CHAPTER03NAME=Encerramento\n")

    # 2. Definição Cirúrgica dos Tiers Neurais
    tier_light = ["Anime4K_Clamp_Highlights.glsl", "Anime4K_Restore_CNN_S.glsl", "Anime4K_Upscale_CNN_x2_S.glsl"]
    tier_balanced = ["Anime4K_Clamp_Highlights.glsl", "Anime4K_Restore_CNN_M.glsl", "Anime4K_Upscale_CNN_x2_M.glsl"]
    tier_extreme = ["Anime4K_Clamp_Highlights.glsl", "Anime4K_Restore_CNN_VL.glsl", "Anime4K_Upscale_CNN_x2_VL.glsl", "Anime4K_AutoDownscalePre_x2.glsl", "Anime4K_AutoDownscalePre_x4.glsl", "Anime4K_Upscale_CNN_x2_M.glsl"]

    def mount_shader(tier):
        validos = [f"{pasta_shaders}/{s}" for s in tier if os.path.exists(os.path.join(pasta_shaders, s))]
        return ":".join(validos) if validos else ""

    s_light = mount_shader(tier_light)
    s_balanced = mount_shader(tier_balanced)
    s_extreme = mount_shader(tier_extreme)

    # 3. Geração Dinâmica dos Atalhos (Fallbacks Manuais)
    with open(arquivo_input, 'w', encoding='utf-8') as f:
        f.write('s seek 90 exact; show-text "Abertura Pulada"\n')
        f.write('Ctrl+0 no-osd change-list glsl-shaders clr ""; show-text "Anime4K: DESATIVADO"\n')
        if s_light: f.write(f'Ctrl+1 no-osd change-list glsl-shaders set "{s_light}"; show-text "Anime4K: Modo LEVE (S)"\n')
        if s_balanced: f.write(f'Ctrl+2 no-osd change-list glsl-shaders set "{s_balanced}"; show-text "Anime4K: Modo BALANCEADO (M)"\n')
        if s_extreme: f.write(f'Ctrl+3 no-osd change-list glsl-shaders set "{s_extreme}"; show-text "Anime4K: Modo EXTREMO (VL)"\n')

    # 4. Argumentos do Motor MPV
    comando_base = [
        "mpv",
        url_video,
        "--fs", 
        f"--force-media-title={titulo_janela}", # Injeta o nome na barra superior
        f"--chapters-file={arquivo_capitulos}", # Injeta as marcações na barra de tempo
        "--script-opts=ytdl_hook-ytdl_path=/usr/local/bin/yt-dlp",
        "--hwdec=auto-safe",
        "--profile=gpu-hq",
        "--deband=yes",              # [ARTEFATOS EXTREMO] Ativa a remoção de banding
        "--deband-iterations=4",     # [ARTEFATOS EXTREMO] 4 varreduras completas no quadro (Esmagamento total)
        "--deband-threshold=60",     # [ARTEFATOS EXTREMO] Força máxima contra blocos de compressão (Macroblocking)
        "--deband-range=30",         # [ARTEFATOS EXTREMO] Raio massivo para fundir cores e sombras
        "--deband-grain=15",         # [ARTEFATOS EXTREMO] Ruído (Dither) elevado para camuflar imperfeições restantes
        "--video-sync=display-resample",
        "--interpolation=yes",
        "--tscale=oversample",
        f"--input-ipc-server={socket_ipc}", # Injeta o Socket de Telemetria
        f"--input-conf={arquivo_input}"
    ]
    
    comando_vulkan = comando_base + ["--vo=gpu-next", "--gpu-api=vulkan"]
    comando_compat = comando_base + ["--vo=gpu"] # Fallback de Compatibilidade (OpenGL padrão)

    # 5. Lógica do Governador (Roda em Thread isolada)
    evento_player = threading.Event()
    modos_ia = {
        0: ("", "Desativado"),
        1: (s_light, "Leve (S)"),
        2: (s_balanced, "Balanceado (M)"),
        3: (s_extreme, "Extremo (VL)")
    }

    def governador_loop():
        current_tier = 3 # Começa no Máximo (Extremo) e deixa o Governador rebaixar se necessário
        last_drops = -1
        estabilidade = 0
        
        # Dá tempo do MPV carregar o buffer do servidor do anime
        time.sleep(3)
        
        # Injeção Inicial
        if s_extreme:
            send_mpv_cmd(socket_ipc, {"command": ["set_property", "glsl-shaders", s_extreme]})
            send_mpv_cmd(socket_ipc, {"command": ["show-text", "Auto-Governor: Modo EXTREMO Iniciado"]})

        while not evento_player.is_set():
            time.sleep(2.5) # Verifica a latência a cada 2.5s
            if not os.path.exists(socket_ipc):
                continue
                
            res = send_mpv_cmd(socket_ipc, {"command": ["get_property", "frame-drop-count"]})
            if res and "data" in res:
                drops_atuais = res["data"]
                if last_drops == -1:
                    last_drops = drops_atuais
                    continue
                    
                diff = drops_atuais - last_drops
                last_drops = drops_atuais

                # Engine Rule 1: Queda brusca de FPS -> Downgrade Imediato
                if diff > 3: 
                    estabilidade = 0
                    if current_tier > 0:
                        current_tier -= 1
                        shader_str, nome = modos_ia[current_tier]
                        send_mpv_cmd(socket_ipc, {"command": ["set_property", "glsl-shaders", shader_str]})
                        send_mpv_cmd(socket_ipc, {"command": ["show-text", f"Auto-Governor: GPU Gargalando! Reduzindo para Modo {nome}"]})
                        
                # Engine Rule 2: Super Estável -> Up-shift de Qualidade Automático
                elif diff == 0:
                    estabilidade += 1
                    if estabilidade >= 25 and current_tier < 3: # ~60 segundos sem perder NENHUM frame
                        current_tier += 1
                        shader_str, nome = modos_ia[current_tier]
                        if shader_str:
                            send_mpv_cmd(socket_ipc, {"command": ["set_property", "glsl-shaders", shader_str]})
                            send_mpv_cmd(socket_ipc, {"command": ["show-text", f"Auto-Governor: GPU Livre! Otimizando para Modo {nome}"]})
                            estabilidade = 0

    thread_gov = threading.Thread(target=governador_loop)
    thread_gov.start()

    with open(arquivo_log, 'a', encoding='utf-8') as f:
        f.write(f"\n[PLAYER] Reproduzindo: {titulo_janela} | URL: {url_video[:50]}...\n")

    try:
        # TENTATIVA 1: Motor Gráfico de Alta Performance (Vulkan)
        subprocess.run(comando_vulkan, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        print("\n[!] Erro Crítico: MPV não encontrado.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        # TENTATIVA 2 (FALLBACK): Motor de Compatibilidade (OpenGL)
        with open(arquivo_log, 'a', encoding='utf-8') as f:
            f.write(f"\n[MPV VULKAN FALHA] Fallback para OpenGL acionado.\n{e.stderr}\n")
            
        print("\n  [!] GPU rejeitou Vulkan. Redirecionando para Modo OpenGL (Compatibilidade)...")
        time.sleep(1.5) # Dá tempo para o OS liberar os ponteiros de rede e limpar o socket IPC
        
        try:
            subprocess.run(comando_compat, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e2:
            with open(arquivo_log, 'a', encoding='utf-8') as f:
                f.write(f"\n[MPV OPENGL CRASH]\n{e2.stderr}\n")
            print("\n[!] Falha crítica dupla no player. Detalhes no 'debug.log'.")
            input("Pressione [ENTER] para voltar...")
    finally:
        # Mata o vigia quando o vídeo for fechado
        evento_player.set()
        thread_gov.join()
        if os.path.exists(socket_ipc):
            try: os.remove(socket_ipc)
            except: pass