import sys
import os
import threading
import itertools
import time
import importlib
import subprocess
import concurrent.futures
from InquirerPy import inquirer, get_style
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from utils.player import assistir_episodio
from utils.storage import carregar_historico, salvar_historico, limpar_historico, gerenciar_tamanho_log, carregar_config, salvar_config
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do arquivo .env automaticamente para o SO

if "--install-playwright" in sys.argv:
    print("Instalando dependências de automação...")
    subprocess.run(["python3", "-m", "playwright", "install", "chromium"])
    sys.exit(0)

# Configuração global de renderização (Tema Cyan/Negrito e Ocultação de cursores)
ESTILO_TUI = get_style({
    "pointer": "ansicyan bold",   # Ponteiro Ciano e Negrito
    "question": "",               # Permite exibir a mensagem principal do InquirerPy
    "answer": "ansicyan bold",    # Cor da resposta selecionada
    "input": "ansicyan",          # Cor do texto de input
    "questionmark": "hidden",     # Esconde o símbolo '?'
})

BANNER = r"""
  █████╗ ██████╗ ███████╗██╗  ██╗██╗  ██╗██╗  ██╗
 ██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██║  ██║██║ ██╔╝
 ███████║██████╔╝█████╗   ╚███╔╝ ███████║█████╔╝ 
 ██╔══██║██╔═══╝ ██╔══╝   ██╔██╗ ╚════██║██╔═██╗ 
 ██║  ██║██║     ███████╗██╔╝ ██╗     ██║██║  ██╗
 ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝     ╚═╝╚═╝  ╚═╝
         [ INTELLIGENCE SYSTEM - A4I ]
"""

def limpar_tela():
    """Limpa a tela e o histórico de rolagem via ANSI Escape."""
    sys.stdout.write('\033[2J\033[3J\033[H') # 2J: limpa tela | 3J: limpa scrollback | H: move cursor p/ topo
    sys.stdout.flush()

def sair_seguro() -> None:
    """Força o encerramento seguro do programa."""
    sys.exit(0)

def animar_carregamento(evento: threading.Event, mensagem: str) -> None:
    """Exibe um spinner assíncrono isolado no buffer principal."""
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    
    limpar_tela()
    print(f"\033[36m{BANNER}\033[0m")
    
    try:
        while not evento.is_set():
            sys.stdout.write(f"\r{next(spinner)} {mensagem}")
            sys.stdout.flush()
            time.sleep(0.08) # Velocidade ajustada para uma animação mais fluida
    finally:
        sys.stdout.write('\r\033[K') 

def verificar_autenticacao_ia():
    """Resolve a API Key do Gemini de forma híbrida (Dev vs Produção PyInstaller)."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    
    # Fallback para o cofre de produção do usuário final
    if not api_key:
        config = carregar_config()
        api_key = config.get("GEMINI_API_KEY", "").strip()
        
    # Prompt interativo na primeira execução sem chave
    if not api_key:
        limpar_tela()
        print(f"\033[36m{BANNER}\033[0m")
        print("  [ REQUISITO DE INTELIGÊNCIA ARTIFICIAL ]\n")
        print("  O Auto-Healing precisa de uma chave gratuita do Google Gemini para reparar scrapers em tempo real.")
        print("  Obtenha a sua chave em: https://aistudio.google.com/app/apikey\n")
        
        try:
            # Mascara o input no terminal por segurança
            api_key = inquirer.secret(
                message=" Cole sua GEMINI_API_KEY (ou ENTER para rodar sem IA):",
                qmark=">",
                amark=">",
                style=ESTILO_TUI
            ).execute().strip()
        except KeyboardInterrupt:
            sair_seguro()
            
        if api_key:
            salvar_config("GEMINI_API_KEY", api_key)
            
    # Injeção em tempo de execução para os módulos lerem via os.environ (Desacoplamento)
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

def main():
    verificar_autenticacao_ia()

    while True: # NÍVEL 1: LOOP DA BUSCA GLOBAL
        limpar_tela()
        # Aplica uma cor ciana no banner para combinar com o tema do InquirerPy
        print(f"\033[36m{BANNER}\033[0m")

        try:
            nome_busca = inquirer.text(
                message=" Informe o nome do anime:\n >",
                qmark="",
                amark="",
                validate=lambda result: len(result.strip()) > 0,
                invalid_message="A entrada de dados não pode ser vazia."
            ).execute()
        except KeyboardInterrupt:
            sair_seguro()

        comando = nome_busca.strip().lower()
        if comando == "/limpar":
            limpar_historico()
            print("\n  [ SISTEMA ] Histórico de reprodução apagado.")
            time.sleep(2)
            continue

        print()
        evento_busca = threading.Event()
        thread_busca = threading.Thread(target=animar_carregamento, args=(evento_busca, "Buscando..."))
        thread_busca.start()
        
        resultados = []
        provedores_ativos = ['animefire', 'animesdigital']
        
        def buscar_no_provedor(provedor):
            try:
                mod = importlib.import_module(f"scrapers.{provedor}")
                return mod.buscar_animes(nome_busca)
            except Exception:
                return []

        # Dispara buscas simultâneas para otimização máxima de latência de rede
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(provedores_ativos)) as executor:
            futuros = [executor.submit(buscar_no_provedor, p) for p in provedores_ativos]
            for futuro in concurrent.futures.as_completed(futuros):
                resultados.extend(futuro.result())
        
        evento_busca.set()
        thread_busca.join()

        if not resultados:
            print("\nNenhum resultado de anime localizado no índice.")
            try:
                input("Pressione ENTER para tentar novamente...")
            except KeyboardInterrupt:
                sair_seguro()
            continue

        
        opcoes_menu = [Separator(" ")]
        for item in resultados:
            texto_exibicao = f"[{item['idioma'].upper()}] [{item['fonte']}] {item['titulo']}"
            opcoes_menu.append(Choice(value=item, name=texto_exibicao))

        opcoes_menu.append(Choice(value=None, name="Voltar"))
        opcoes_menu.append(Choice(value="sair", name="Sair"))

        while True: # NÍVEL 2: LOOP DA LISTA DE ANIMES
            limpar_tela()
            print(f"\033[36m{BANNER}\033[0m")
            try:
                anime_escolhido = inquirer.select(
                    message="  Escolha uma opção:",
                    choices=opcoes_menu,
                    pointer="❯",            # Caractere de ponteiro atualizado
                    style=ESTILO_TUI,
                    qmark="",
                    amark="",
                    instruction="", # Remove as instruções visuais do InquirerPy, eliminando a "barra de digitação"
                    max_height="100%",      # Permite que a lista ocupe toda a altura disponível do terminal
                    default=opcoes_menu[1].value
                ).execute()
            except KeyboardInterrupt:
                sair_seguro()

            if anime_escolhido is None:
                break # Quebra Nível 2 e retorna para o Nível 1 (Busca Inicial)
            elif anime_escolhido == "sair":
                limpar_tela()
                print("Apex4k encerrado...")
                sair_seguro()

            # Extrai apenas o nome do provedor base (ignorando sufixos como "(Força Bruta)")
            fonte_base = anime_escolhido['fonte'].split('(')[0].strip()
            fonte_formatada = fonte_base.lower().replace(" ", "")
            modulo_provedor = importlib.import_module(f"scrapers.{fonte_formatada}")

            print()
            evento_eps = threading.Event()
            thread_eps = threading.Thread(target=animar_carregamento, args=(evento_eps, "Carregando a lista de episódios..."))
            thread_eps.start()
            
            episodios = modulo_provedor.buscar_episodios(anime_escolhido['link'])
            
            evento_eps.set()
            thread_eps.join()

            if not episodios:
                print("\nNenhum episódio localizado na extração de dados.")
                try:
                    input("Pressione ENTER para voltar...")
                except KeyboardInterrupt:
                    sair_seguro()
                continue # Falha mantida, recomeça Nível 2

            historico = carregar_historico()
            registro_anime = historico.get(anime_escolhido['titulo'])
            
            # Retrocompatibilidade: Suporta o formato novo (dict) e o formato antigo (int)
            if isinstance(registro_anime, dict):
                ultimo_ep_visto = registro_anime.get('episodio', -1)
            elif isinstance(registro_anime, int):
                ultimo_ep_visto = registro_anime
            else:
                ultimo_ep_visto = -1
            
            if ultimo_ep_visto >= len(episodios) and ultimo_ep_visto != -1:
                ultimo_ep_visto = 0

            while True: # NÍVEL 3: LOOP DE EPISÓDIOS
                opcoes_ep = [Separator(" ")]
                for i, ep in enumerate(episodios):
                    # Se for o último visto, ganha a estrela. Se não, ganha dois espaços para manter o alinhamento.
                    if i == ultimo_ep_visto and ultimo_ep_visto != -1:
                        marcador = " [ÚLTIMO REPRODUZIDO]" # Símbolo seguro e limpo
                    else:
                        marcador = "" # Dois espaços garantem o alinhamento perfeito da lista
                        
                    nome_exibicao = f"[{anime_escolhido['titulo']}] - {ep['nome']}{marcador}"
                    opcoes_ep.append(Choice(value=i, name=nome_exibicao))
                
                opcoes_ep.append(Choice(value=-1, name="Voltar"))
                opcoes_ep.append(Choice(value="sair", name="Sair"))

                limpar_tela()
                print(f"\033[36m{BANNER}\033[0m")
                
                try:
                    idx_escolhido = inquirer.select(
                        message="  Escolha uma opção:",
                        choices=opcoes_ep,
                        pointer="❯",            # Caractere de ponteiro atualizado
                        style=ESTILO_TUI,
                        qmark="",
                        amark="",
                        instruction="",
                        max_height="100%",      # Permite que a lista ocupe toda a altura disponível do terminal
                        default=ultimo_ep_visto if ultimo_ep_visto != -1 else 0
                    ).execute()
                except KeyboardInterrupt:
                    sair_seguro()

                if idx_escolhido == -1:
                    break # Quebra Nível 3 e retorna para o Nível 2 (Lista de Animes)
                elif idx_escolhido == "sair":
                    limpar_tela()
                    print("Apex4k encerrado...")
                    sair_seguro()

                while True: # NÍVEL 4: REPRODUÇÃO E PÓS-VÍDEO
                    ultimo_ep_visto = idx_escolhido 
                    
                    ep_atual = episodios[idx_escolhido]
                    salvar_historico(anime_escolhido['titulo'], anime_escolhido['fonte'], idx_escolhido)
                    
                    # Feedback visual assíncrono para o Playwright não congelar a interface TUI
                    evento_extracao = threading.Event()
                    thread_extracao = threading.Thread(target=animar_carregamento, args=(evento_extracao, f"Carregando stream ({anime_escolhido['titulo']} - {ep_atual['nome']})..."))
                    thread_extracao.start()
                    
                    link_puro = modulo_provedor.extrair_link_mp4(ep_atual['link'])
                    
                    evento_extracao.set()
                    thread_extracao.join()
                    limpar_tela()
                    print(f"\033[36m{BANNER}\033[0m")
                    
                    assistir_episodio(link_puro, anime_escolhido['titulo'], ep_atual['nome'])

                    # --- MENU PÓS-VÍDEO ---
                    limpar_tela()
                    print(f"\033[36m{BANNER}\033[0m")
                    opcoes_pos = [Separator(" ")]
                    
                    if idx_escolhido < len(episodios) - 1:
                        opcoes_pos.append(Choice(value="prox", name="[Próximo Episódio]"))
                    if idx_escolhido > 0:
                        opcoes_pos.append(Choice(value="ant", name="[Episódio Anterior]"))
                        
                    opcoes_pos.append(Choice(value="lista", name="Voltar"))
                    opcoes_pos.append(Choice(value="sair", name="Sair"))

                    try:
                        acao = inquirer.select(
                            message=f"  Reprodução concluída ({anime_escolhido['titulo']} - {ep_atual['nome']}).\n  Selecione a próxima ação:",
                            choices=opcoes_pos,
                            pointer="❯",            # Caractere de ponteiro atualizado
                            style=ESTILO_TUI,
                            qmark="",
                            amark="",
                            instruction="",
                            max_height="100%"       # Permite que a lista ocupe toda a altura disponível do terminal
                        ).execute()
                    except KeyboardInterrupt:
                        sair_seguro()

                    if acao == "prox":
                        idx_escolhido += 1 
                        continue 
                    elif acao == "ant":
                        idx_escolhido -= 1 
                        continue 
                    elif acao == "lista":
                        break # Quebra Nível 4 e retorna para o Nível 3 (Lista de Episódios)
                    elif acao == "sair":
                        limpar_tela()
                        print("Apex4k encerrado...")
                        sair_seguro()

if __name__ == "__main__":
    main()