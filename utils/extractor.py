import os
from playwright.sync_api import sync_playwright

ARQUIVO_LOG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'debug.log'))
USER_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.browser_session'))

def interceptar_video_playwright(url_episodio: str) -> str:
    streams_candidatos = set()

    def capturar_rota(rota):
        url_req = rota.request.url
        url_lower = url_req.lower()

        # Aborta imagens e CSS para velocidade
        if rota.request.resource_type in ["image", "stylesheet", "font"]:
            try: rota.abort(); return
            except: pass
            
        # ALLOWLIST ESTRITA: O anime real sempre será HLS (.m3u8) ou Google (Drive/Blogger).
        # Ignora silenciosamente qualquer .mp4 genérico (que é de onde vêm os vídeos de anúncios).
        is_hls = '.m3u8' in url_lower and 'segment' not in url_lower and '.ts' not in url_lower
        is_google = 'googlevideo.com' in url_lower or 'blogger.com' in url_lower
        
        if is_hls or is_google:
            streams_candidatos.add(url_req)
            
        try: rota.continue_()
        except: pass

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled', '--mute-audio']
            )
            
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page = context.pages[0] if context.pages else context.new_page()
            page.route("**/*", capturar_rota)
            
            page.goto(url_episodio, wait_until="domcontentloaded", timeout=15000)
            
            try:
                page.mouse.click(page.viewport_size['width'] / 2, page.viewport_size['height'] / 2)
                page.evaluate("() => { let btn = document.querySelector('.dooplay_player_option'); if(btn) btn.click(); }")
                for frame in page.frames:
                    frame.evaluate("() => { let btn = document.querySelector('button, .play-button, .vjs-big-play-button'); if(btn) btn.click(); else document.body.click(); }")
            except: pass
            
            # Polling com limite de 5 segundos
            for _ in range(10): 
                page.wait_for_timeout(500)
                if any(padrao in u.lower() for u in streams_candidatos for padrao in ['1080', 'itag=37', 'master.m3u8']):
                    break
            context.close()
    except Exception as e:
        with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n[PLAYWRIGHT ERRO EXTRACTOR] {e}\n")
        
    # Heurística final: Devolve a master playlist ou o link de maior qualidade retido
    lista_urls = list(streams_candidatos)
    if not lista_urls: 
        return url_episodio
    
    for url in lista_urls:
        if 'master' in url.lower() or '1080' in url.lower() or 'itag=37' in url.lower():
            return url
            
    return lista_urls[-1]