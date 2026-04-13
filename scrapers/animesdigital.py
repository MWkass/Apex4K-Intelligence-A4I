import cloudscraper
from bs4 import BeautifulSoup
from typing import List, Dict
import os
import sys
import traceback
import urllib.parse
import re
from utils.extractor import interceptar_video_playwright
from utils.ai_agent import reparar_busca_animes, reparar_busca_episodios

if getattr(sys, 'frozen', False):
    DIRETORIO_RAIZ = os.path.dirname(sys.executable)
else:
    DIRETORIO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARQUIVO_LOG = os.path.join(DIRETORIO_RAIZ, 'debug.log')

def obter_scraper_seguro():
    return cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )

def buscar_animes(nome_anime: str) -> List[Dict[str, str]]:
    url = f"https://animesdigital.org/?s={nome_anime.replace(' ', '+')}"
    
    try:
        scraper = obter_scraper_seguro()
        resposta = scraper.get(url, timeout=7) # Reduzido para fail-fast
        resposta.raise_for_status() # Força o Python a acusar erro 403 (Cloudflare) ou 404
        soup = BeautifulSoup(resposta.text, 'html.parser')
        resultados = []
        
        # O layout mudou, 'itemA' e 'itemE' não são mais usados para resultados de busca.
        # Agora, os resultados estão dentro de 'div.b_flex.b_wrap' e são links diretos.
        resultados_container = soup.find('div', class_='b_flex b_wrap')
        caixas_animes = []
        if resultados_container:
            # Procura por links de animes dentro do novo container, filtrando por '/anime/' no href.
            caixas_animes = resultados_container.find_all('a', href=lambda href: href and '/anime/' in href)
            
        for caixa in caixas_animes:
            # 'caixa' já é a tag 'a' devido ao find_all('a', ...)
            # O título agora é o texto direto da tag 'a', com fallback para o atributo 'title'
            if caixa and caixa.has_attr('href'):
                titulo = caixa.text.strip()
                if not titulo: # Se o texto estiver vazio, tenta o atributo 'title'
                    titulo = caixa.get('title', '').strip()
                
                if titulo:
                    # Lógica Heurística de Classificação de Idioma
                    if "Dublado" in titulo or "(Dublado)" in titulo:
                        idioma = "Dublado"
                        titulo_limpo = titulo.replace("(Dublado)", "").replace("Dublado", "").strip()
                    else:
                        idioma = "Legendado"
                        titulo_limpo = titulo
                        
                    resultados.append({
                        "titulo": titulo_limpo,
                        "link": caixa['href'],
                        "idioma": idioma,
                        "fonte": "AnimesDigital"
                    })

        # --- FALLBACK: SLUG GUESSING (FORÇA BRUTA) ---
        if not resultados:
            # Limpa o nome do anime para gerar um slug compatível com a URL (ex: "Kanan-sama" -> "kanan-sama")
            slug_base = re.sub(r'[^a-z0-9]+', '-', nome_anime.lower()).strip('-')
            
            urls_tentativas = [
                f"https://animesdigital.org/anime/{slug_base}",
                f"https://animesdigital.org/anime/{slug_base}-dublado"
            ]
            
            for url_guess in urls_tentativas:
                try:
                    # Não acionamos raise_for_status() aqui, pois o erro 404 (Não Encontrado) é natural no chute
                    resposta_guess = scraper.get(url_guess, timeout=5)
                    if resposta_guess.status_code == 200:
                        soup_guess = BeautifulSoup(resposta_guess.text, 'html.parser')
                        titulo_h1 = soup_guess.find('h1')
                        
                        # Extrai o título real se a tag h1 existir, caso contrário capitaliza o termo de busca
                        titulo_real = titulo_h1.text.strip() if titulo_h1 else nome_anime.title()
                        idioma = "Dublado" if "dublado" in url_guess or "Dublado" in titulo_real else "Legendado"
                        titulo_limpo = titulo_real.replace("(Dublado)", "").replace("Dublado", "").strip()
                        
                        resultados.append({
                            "titulo": titulo_limpo,
                            "link": url_guess,
                            "idioma": idioma,
                            "fonte": "Animes Digital"
                        })
                except Exception:
                    continue  # Abafa erros de timeout ou conexão para não travar a varredura
                
        texto_pagina = soup.text.lower()
        anime_inexistente = any(msg in texto_pagina for msg in ['nenhum resultado', 'não encontrado', 'nada encontrado', 'nenhum anime'])
        
        if not resultados and soup.text and not anime_inexistente:
            # [IA AGENTE] Self-Healing: Acionado apenas se o site carregou, mas a extração falhou por layout
            resultados = reparar_busca_animes(resposta.text, "AnimesDigital", __file__)
            if not resultados:
                with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
                    f.write(f"[AnimesDigital] A busca não retornou nenhum resultado válido nem via IA.\n")
                
        return resultados
    except Exception as e:
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[AnimesDigital] Erro de Rede/Cloudflare: {e}\n{traceback.format_exc()}\n")
        return []

def buscar_episodios(url_anime: str) -> List[Dict[str, str]]:
    try:
        scraper = obter_scraper_seguro()
        # Aumentado para 15s para dar margem à resolução de Cloudflare
        resposta = scraper.get(url_anime, timeout=15)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, 'html.parser')
        episodios = []
        urls_vistas = set()
        
        # 1. Tenta extrair pela estrutura de boxes (itemE)
        caixas_eps = soup.find_all('div', class_='itemE')
        if caixas_eps:
            for caixa in caixas_eps:
                tag_link = caixa.find('a')
                if tag_link and tag_link.has_attr('href'):
                    href = tag_link['href']
                    if href not in urls_vistas:
                        urls_vistas.add(href)
                        num_span = caixa.find('span', class_='number')
                        nome_bruto = num_span.text.strip() if num_span else tag_link.text.strip()
                        
                        # Extração cirúrgica do número do episódio
                        match = re.search(r'(?i)epis[óo]dio\s*(\d+)', nome_bruto)
                        if match:
                            nome_ep = f"Episódio {match.group(1).zfill(2)}"
                        else:
                            # Remove ícones e textos de "X minutos atrás"
                            nome_ep = re.sub(r'(?i)(smart_display|\d+\s*(segundos?|minutos?|horas?|dias?)\s*atr[áa]s)', '', nome_bruto).strip()
                            nome_ep = " ".join(nome_ep.split())
                            
                        episodios.append({
                            "nome": nome_ep if len(nome_ep) > 1 else f"Episódio {len(episodios)+1}",
                            "link": href
                        })
                        
        # 2. Se falhar, usa Seletores CSS clássicos + Fallback Heurístico (Apenas Links de Episódio)
        if not episodios:
            links = soup.select('a.episode-link, .episodios li a, .episodesList a')
            if not links:
                # O "Salvador da Pátria": lê qualquer link que tenha a palavra "episodio" ou "video"
                links = soup.find_all('a', href=lambda x: x and ('-episodio-' in x.lower() or '/episodio/' in x.lower() or '/video/' in x.lower()))
                
            for a in links:
                href = a['href']
                if href not in urls_vistas and href != url_anime:
                    urls_vistas.add(href)
                    nome_bruto = a.text.strip()
                    if not nome_bruto:
                        nome_bruto = a.get('title', f"Episódio {len(episodios)+1}")
                    
                    match = re.search(r'(?i)epis[óo]dio\s*(\d+)', nome_bruto)
                    if match:
                        nome = f"Episódio {match.group(1).zfill(2)}"
                    else:
                        nome = re.sub(r'(?i)(smart_display|\d+\s*(segundos?|minutos?|horas?|dias?)\s*atr[áa]s)', '', nome_bruto).strip()
                        nome = " ".join(nome.split())
                        
                    episodios.append({
                        "nome": nome if len(nome) > 1 else f"Episódio {len(episodios)+1}",
                        "link": href
                    })
                    
        # [IA AGENTE] Self-Healing para Episódios
        if not episodios and soup.text:
            episodios = reparar_busca_episodios(resposta.text, url_anime, "AnimesDigital", __file__)

        # Heurística de Ordenação: Inverte a lista se ela vier do maior para o menor
        if len(episodios) > 1:
            match_primeiro = re.search(r'(\d+)', episodios[0]['nome'])
            match_ultimo = re.search(r'(\d+)', episodios[-1]['nome'])
            if match_primeiro and match_ultimo:
                if int(match_primeiro.group(1)) > int(match_ultimo.group(1)):
                    episodios.reverse()

        return episodios
    except Exception as e:
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[AnimesDigital Episódios] Erro: {e}\n{traceback.format_exc()}\n")
        return []

def extrair_link_mp4(url_episodio: str) -> str:
    """Entra na página de vídeo, encontra o IFrame e extrai a URL direta de streaming (HLS/MP4)."""
    # Delegação da resolução de vídeo para Automação Web via Playwright
    return interceptar_video_playwright(url_episodio)