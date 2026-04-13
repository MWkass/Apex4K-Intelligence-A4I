import cloudscraper
from bs4 import BeautifulSoup
import re
from typing import List, Dict
from utils.ai_agent import reparar_busca_animes, reparar_busca_episodios

def obter_scraper_seguro():
    """Gera um cliente de rede camuflado com assinaturas reais de navegador para burlar CF."""
    return cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )

def buscar_animes(nome_anime: str) -> List[Dict[str, str]]:
    """
    Busca o anime e retorna uma lista de dicionários com os resultados limpos.
    """
    busca_formatada = nome_anime.replace(' ', '-').lower()
    url = f"https://animefire.plus/pesquisar/{busca_formatada}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }

    try:
        scraper = obter_scraper_seguro()
        resposta = scraper.get(url, headers=headers, timeout=15)
        resposta.raise_for_status()
        
        soup = BeautifulSoup(resposta.text, 'html.parser')
        resultados = []
        caixas_animes = soup.find_all('div', class_='divCardUltimosEps')
        
        for caixa in caixas_animes:
            tag_link = caixa.find('a')
            if tag_link:
                titulo_bruto = tag_link.text.strip()
                link = tag_link['href']
                
                if titulo_bruto and link:
                    # Limpeza de Dados: Remove espaços extras, notas (ex: 7.42) e classificação (ex: A14)
                    titulo_limpo = re.sub(r'\s+\d+\.\d+\s+[A-Z\d]+$', '', titulo_bruto).strip()
                    # Remove caracteres invisíveis do HTML (como o &nbsp;)
                    titulo_limpo = titulo_limpo.replace('\xa0', ' ')
                    
                    # Lógica de Classificação de Idioma
                    if "(Dublado)" in titulo_limpo:
                        idioma = "Dublado"
                        # Opcional: removemos a palavra do título para a interface ficar mais limpa
                        titulo_limpo = titulo_limpo.replace("(Dublado)", "").strip()
                    else:
                        idioma = "Legendado"

                    resultados.append({
                        "titulo": titulo_limpo,
                        "link": link,
                        "idioma": "Dublado" if "Dublado" in idioma else "Legendado",
                        "fonte": "Animefire"
                    })
                    
        # [IA AGENTE] Self-Healing: Verifica se não é apenas uma busca vazia legítima antes de acionar a IA
        texto_pagina = soup.text.lower()
        anime_inexistente = any(msg in texto_pagina for msg in ['nenhum resultado', 'não encontrado', 'nada encontrado', 'nenhum anime'])
        
        if not resultados and soup.text and not anime_inexistente:
            resultados = reparar_busca_animes(resposta.text, "Animefire", __file__)

        return resultados
    except Exception as e:
        print(f"Erro de conectividade ao buscar animes: {e}")
        return []

def buscar_episodios(url_anime: str) -> List[Dict[str, str]]:
    """
    Entra na página do anime e extrai a lista de episódios disponíveis.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }

    try:
        scraper = obter_scraper_seguro()
        resposta = scraper.get(url_anime, headers=headers, timeout=15)
        resposta.raise_for_status()
        
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        episodios = []
        urls_vistas = set()
        
        # 1. Pegamos o "slug" (nome base) do anime pela URL
        # Ex: ".../animes/boruto-todos-os-episodios" vira "boruto"
        slug_anime = url_anime.split('/')[-1].replace('-todos-os-episodios', '')
        
        links = soup.find_all('a', href=True)
        
        for a in links:
            href = a['href']
            
            # 2. Nova Lógica: Procuramos links que tenham "/animes/slug-do-anime/numero"
            if f"/animes/{slug_anime}/" in href:
                texto = a.text.strip()
                numero_ep = href.split('/')[-1] # Pega o número no final da URL
                
                # Se o texto do link for vazio ou muito genérico, criamos um nome bonito
                nome_bruto = texto if texto and len(texto) > 1 else f"Episódio {numero_ep}"
                
                # Padronização Visual e Limpeza
                match = re.search(r'(?i)epis[óo]dio\s*(\d+)', nome_bruto)
                if match:
                    nome_ep = f"Episódio {match.group(1).zfill(2)}"
                else:
                    nome_ep = re.sub(r'(?i)(smart_display|\d+\s*(segundos?|minutos?|horas?|dias?)\s*atr[áa]s)', '', nome_bruto).strip()
                
                if href not in urls_vistas:
                    urls_vistas.add(href)
                    episodios.append({
                        "nome": nome_ep if len(nome_ep) > 1 else f"Episódio {numero_ep}",
                        "link": href
                    })
                    
        # [IA AGENTE] Self-Healing para Episódios
        if not episodios and soup.text:
            episodios = reparar_busca_episodios(resposta.text, url_anime, "Animefire", __file__)
            
        return episodios
    except Exception as e:
        print(f"Erro de conectividade ao buscar episódios: {e}")
        return []

def extrair_link_mp4(url_episodio: str) -> str:
    """
    Entra na página do episódio, procura a API de vídeo oculta e extrai o link direto (.mp4).
    """
    print("Extraindo link de vídeo de alta performance...")
    
    try:
        scraper = obter_scraper_seguro()
        # 1. Acessa a página do episódio
        resposta = scraper.get(url_episodio, timeout=15)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # 2. Encontra a tag <video> que contém a rota da API
        video_tag = soup.find('video')
        
        if not video_tag or 'data-video-src' not in video_tag.attrs:
            print("Aviso: Estrutura de vídeo original mantida (API não interceptada).")
            return url_episodio # Devolve o original para tentar a sorte
            
        url_api_json = video_tag['data-video-src']
        
        # 3. Fazemos uma segunda requisição, agora para a API, que nos devolve um JSON
        resposta_api = scraper.get(url_api_json, timeout=15)
        dados_video = resposta_api.json()
        
        # 4. O JSON do Animefire possui uma lista chamada 'data'.
        # Cada item tem um 'src' (o link mp4) e um 'label' (SD, HD).
        link_direto = None
        for qualidade in dados_video.get('data', []):
            link_direto = qualidade.get('src')
            # O loop vai sobrescrevendo, e como a lista geralmente termina no HD,
            # ele vai armazenar a melhor qualidade disponível!
            
        return link_direto if link_direto else url_episodio
    except Exception:
        print("Falha ao resolver API de vídeo nativo. Retornando URL de fallback.")
        return url_episodio