import os
import json
import sys
from bs4 import BeautifulSoup
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

if getattr(sys, 'frozen', False):
    DIRETORIO_RAIZ = os.path.dirname(sys.executable)
else:
    DIRETORIO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARQUIVO_LOG = os.path.join(DIRETORIO_RAIZ, 'debug.log')

def limpar_html_para_ia(html: str) -> str:
    """Minimiza o DOM removendo tags visuais/lógicas inúteis para economizar tokens e acelerar a IA."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'svg', 'img', 'noscript', 'meta']):
            tag.decompose()
        # Corta em 40 mil caracteres como margem de segurança do contexto
        return str(soup.body)[:40000] if soup.body else str(soup)[:40000]
    except Exception:
        return html[:40000]

def aplicar_auto_reparo(caminho_arquivo: str, correcao: dict, provedor: str, alvo: str) -> None:
    """Lê o arquivo Python, localiza o código defasado e o sobrescreve com a correção da IA."""
    try:
        # Arquitetura Segura: Extrai os dados na memória para o usuário assistir, 
        # mas sugere a mudança de código no log em vez de injetar código cego no sistema.
        trecho_novo = correcao.get("trecho_novo_corrigido", "")
        explicacao = correcao.get("explicacao", "Sem detalhes fornecidos.")
        
        mensagem = (
            f"\n{'='*50}\n"
            f"[SUGESTÃO DE REPARO IA] {provedor} ({alvo})\n"
            f"Motivo: {explicacao}\n\nCódigo Sugerido para substituir:\n{trecho_novo}\n"
            f"{'='*50}\n"
        )
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write(mensagem)
    except Exception:
        pass

def reparar_busca_animes(html_bruto: str, provedor: str, caminho_arquivo: str) -> List[Dict[str, str]]:
    """Agente Gemini: Invocado quando o scraper estrutural falha na varredura da busca."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return []

    try:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel
        
        class AnimeExtraido(BaseModel):
            titulo: str
            link: str
            idioma: str

        class CorrecaoCodigo(BaseModel):
            trecho_antigo_exato: str
            trecho_novo_corrigido: str
            explicacao: str

        class ReparoBusca(BaseModel):
            resultados: List[AnimeExtraido]
            correcao: CorrecaoCodigo
            
        client = genai.Client(api_key=api_key) # Força a leitura da chave explicitamente
        html_limpo = limpar_html_para_ia(html_bruto)
        
        # Lê o próprio código fonte para a IA analisar
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            codigo_fonte = f.read()
        
        prompt = f"""
        O scraper do site '{provedor}' quebrou pois o layout mudou.
        TAREFA 1: Extraia a lista de animes (título, link, idioma) do HTML fornecido.
        TAREFA 2: Analise o CÓDIGO FONTE PYTHON abaixo e identifique qual bloco exato do BeautifulSoup falhou na função `buscar_animes`.
        Devolva o 'trecho_antigo_exato' copiando LITERALMENTE os espaços e quebras de linha (para podermos fazer um string.replace perfeito) e devolva o 'trecho_novo_corrigido' com a nova lógica.
        
        CÓDIGO FONTE PYTHON ATUAL:
        ```python
        {codigo_fonte}
        ```
        """
        
        instrucao = "Você é um Engenheiro de Software Sênior focado em Python e BeautifulSoup. Responda apenas com o JSON estruturado."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, html_limpo],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReparoBusca,
                system_instruction=instrucao,
                temperature=0.0, # Foco puramente analítico e determinístico
            ),
        )
        
        dados = json.loads(response.text)
        resultados = []
        
        for item in dados.get("resultados", []):
            resultados.append({
                "titulo": item["titulo"],
                "link": item["link"],
                "idioma": item.get("idioma", "Legendado"),
                "fonte": f"{provedor} (IA)"
            })
            
        if "correcao" in dados:
            aplicar_auto_reparo(caminho_arquivo, dados["correcao"], provedor, "buscar_animes")
            
        return resultados
        
    except ImportError:
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write("\n[IA SELF-HEALING ERRO] Instale as libs: pip install google-genai pydantic\n")
        return []
    except Exception as e:
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n[IA SELF-HEALING ERRO] Busca: {e}\n")
        return []

def reparar_busca_episodios(html_bruto: str, url_anime: str, provedor: str, caminho_arquivo: str) -> List[Dict[str, str]]:
    """Agente Gemini: Invocado quando o scraper estrutural falha na captura de episódios."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return []

    try:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel
        
        class EpisodioExtraido(BaseModel):
            nome: str
            link: str
            
        class CorrecaoCodigo(BaseModel):
            trecho_antigo_exato: str
            trecho_novo_corrigido: str
            explicacao: str
            
        class ReparoEpisodios(BaseModel):
            episodios: List[EpisodioExtraido]
            correcao: CorrecaoCodigo
            
        client = genai.Client(api_key=api_key)
        html_limpo = limpar_html_para_ia(html_bruto)
        
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            codigo_fonte = f.read()
            
        prompt = f"""
        O scraper do site '{provedor}' quebrou na página de episódios.
        URL Base analisada: {url_anime}
        TAREFA 1: Extraia a lista completa de episódios (nome amigável e link) do HTML.
        TAREFA 2: Analise o CÓDIGO PYTHON abaixo e crie um patch de código. Encontre o laço for ou o seletor `.find_all` que está quebrado na função `buscar_episodios`.
        Devolva o 'trecho_antigo_exato' (cópia fiel) e o 'trecho_novo_corrigido' com os seletores atualizados.
        
        CÓDIGO FONTE PYTHON ATUAL:
        ```python
        {codigo_fonte}
        ```
        """
        
        response = client.models.generate_content(
            model='gemini-3.0-flash',
            contents=[prompt, html_limpo],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReparoEpisodios,
                temperature=0.0,
            ),
        )
        
        dados = json.loads(response.text)
        episodios = [{"nome": ep["nome"], "link": ep["link"]} for ep in dados.get("episodios", [])]
        
        if "correcao" in dados:
            aplicar_auto_reparo(caminho_arquivo, dados["correcao"], provedor, "buscar_episodios")
            
        return episodios
        
    except Exception as e:
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n[IA SELF-HEALING ERRO] Episódios: {e}\n")
        return []