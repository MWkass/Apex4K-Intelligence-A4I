import json
import os
import sys
from typing import Dict, Any

# Descobre a pasta principal do projeto e crava o arquivo lá de forma absoluta
if getattr(sys, 'frozen', False):
    DIRETORIO_RAIZ = os.path.dirname(sys.executable)
else:
    DIRETORIO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

ARQUIVO_HISTORICO = os.path.join(DIRETORIO_RAIZ, "historico.json")
ARQUIVO_CONFIG = os.path.join(DIRETORIO_RAIZ, "config.json")

def carregar_historico() -> Dict[str, Any]:
    """Lê o arquivo JSON e retorna um dicionário com o histórico."""
    # Se o arquivo não existe (primeira vez rodando), retorna um dicionário vazio
    if not os.path.exists(ARQUIVO_HISTORICO):
        return {}
    
    try:
        with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # Tratamento silencioso de falhas de I/O (corrupção), garantindo estado inicial
        return {}

def salvar_historico(titulo_anime: str, fonte: str, index_episodio: int) -> None:
    """Salva o índice do episódio atual e a fonte no histórico do anime."""
    historico = carregar_historico()
    
    # Atualiza o dicionário com o novo formato, incluindo a tag da fonte
    historico[titulo_anime] = {
        "episodio": index_episodio,
        "fonte": fonte
    }
    
    try:
        with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=4, ensure_ascii=False)
    except Exception:
        pass  # Evita crash do programa caso não haja permissão de escrita no sistema

def limpar_historico() -> None:
    """Apaga todos os registros do histórico de reprodução."""
    try:
        with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def gerenciar_tamanho_log() -> None:
    """Rotaciona o debug.log caso ele ultrapasse 2MB de tamanho."""
    arquivo_log = os.path.join(DIRETORIO_RAIZ, "debug.log")
    limite_mb = 2 * 1024 * 1024 # 2 Megabytes em bytes
    
    try:
        if os.path.exists(arquivo_log) and os.path.getsize(arquivo_log) > limite_mb:
            with open(arquivo_log, 'w', encoding='utf-8') as f:
                f.write("[ SISTEMA ] Arquivo de log rotacionado automaticamente (Excedeu 2MB).\n")
    except Exception:
        pass

def carregar_config() -> Dict[str, Any]:
    """Lê o arquivo de configurações gerais do usuário."""
    if not os.path.exists(ARQUIVO_CONFIG):
        return {}
    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_config(chave: str, valor: Any) -> None:
    """Persiste uma chave de configuração no cofre local."""
    config = carregar_config()
    config[chave] = valor
    try:
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass