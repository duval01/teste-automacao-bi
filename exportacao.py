import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_log.txt", mode='w', encoding='utf-8'), # Salva em arquivo
        logging.StreamHandler() # Mostra no terminal
    ]
)

# --- CONFIGURAÇÕES DO TESTE ---
URL_ALVO = "COLOQUE_A_URL_AQUI"  # <--- INSIRA A URL DO SITE AQUI
SELETOR_ALVO = "input.searchInput"

def run():
    with sync_playwright() as p:
        # headless=False permite que você veja o navegador abrindo
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        logging.info(f"Iniciando navegação para: {URL_ALVO}")
        
        try:
            page.goto(URL_ALVO, timeout=60000)
            
            # 1. Espera a rede acalmar (crucial para dashboards pesados)
            logging.info("Aguardando carregamento da rede (networkidle)...")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except:
                logging.warning("Networkidle demorou, prosseguindo mesmo assim...")

            # 2. Tenta localizar o elemento (Lógica Inteligente: Página vs Iframes)
            logging.info(f"Procurando pelo seletor: '{SELETOR_ALVO}'")
            
            elemento_encontrado = None
            frame_encontrado = None

            # Tentativa A: Na página principal
            try:
                # Espera curta para verificar a página principal
                page.locator(SELETOR_ALVO).wait_for(state="visible", timeout=5000)
                elemento_encontrado = page.locator(SELETOR_ALVO)
                logging.info("Elemento encontrado na página principal (Main Frame).")
            except:
                logging.info("Não encontrado no Main Frame. Verificando Iframes...")

            # Tentativa B: Iterar sobre todos os Iframes (se falhou na principal)
            if not elemento_encontrado:
                for frame in page.frames:
                    try:
                        # Tenta achar dentro do frame sem esperar muito (check rápido)
                        if frame.locator(SELETOR_ALVO).is_visible():
                            elemento_encontrado = frame.locator(SELETOR_ALVO)
                            frame_encontrado = frame
                            logging.info(f"SUCESSO! Elemento encontrado dentro do iframe: {frame.url}")
                            break
                    except:
                        continue

            # 3. Ação ou Erro Final
            if elemento_encontrado:
                logging.info("Tentando interagir com o campo...")
                elemento_encontrado.highlight() # Destaca o campo em rosa/vermelho visualmente
                elemento_encontrado.click()
                elemento_encontrado.fill("Teste Município") # Tenta preencher
                logging.info("Interação realizada com sucesso!")
                
                # Pausa para você ver o resultado antes de fechar
                time.sleep(5) 
                
            else:
                raise Exception("Elemento não encontrado em nenhum lugar (Main ou Frames).")

        except Exception as e:
            logging.error(f"FALHA FATAL: {e}")
            
            # --- COLETA DE EVIDÊNCIAS ---
            logging.info("Gerando evidências do erro...")
            
            # 1. Screenshot do momento do erro
            page.screenshot(path="debug_erro_screenshot.png", full_page=True)
            logging.info("Screenshot salvo como 'debug_erro_screenshot.png'")
            
            # 2. Dump do HTML (para você procurar onde o elemento foi parar)
            with open("debug_pagina.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            logging.info("HTML da página salvo como 'debug_pagina.html'")

        finally:
            browser.close()
            logging.info("Navegador fechado.")

if __name__ == "__main__":
    if URL_ALVO == "COLOQUE_A_URL_AQUI":
        print("ERRO: Você precisa editar o script e colocar a URL na variável URL_ALVO antes de rodar.")
    else:
        run()
