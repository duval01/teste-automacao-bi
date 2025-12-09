from playwright.sync_api import sync_playwright
import os
import time

def diagnosticar_tela(report_url):
    if not os.path.exists("auth.json"):
        print("ERRO: auth.json não encontrado.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Headless False para você ver
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()

        print(f"Acessando: {report_url}")
        page.goto(report_url)
        
        # Espera genérica para carregamento visual
        time.sleep(10) 
        
        print("\n--- INÍCIO DO DIAGNÓSTICO ---")
        print(f"Título da Página: {page.title()}")
        
        # Lista todos os botões visíveis na página
        print("\nListando botões visíveis:")
        botoes = page.get_by_role("button").all()
        
        found_export = False
        for i, btn in enumerate(botoes):
            try:
                if btn.is_visible():
                    texto = btn.text_content().strip()
                    label = btn.get_attribute("aria-label") or "Sem Label"
                    print(f"Botão {i}: Texto='{texto}' | Label='{label}'")
                    
                    if "xport" in texto or "xport" in label:
                        found_export = True
                        print(f"   >>> POSSÍVEL ALVO ENCONTRADO ACIMA! <<<")
            except:
                pass

        print("\n--- FIM DO DIAGNÓSTICO ---")
        
        if not found_export:
            print("AVISO: Nenhum botão com nome 'Export' ou 'Exportar' foi detectado.")
            print("Pode ser que esteja dentro de um menu 'Arquivo' ou seja apenas um ícone.")
        
        input("Pressione ENTER aqui no terminal para fechar o navegador...")
        browser.close()

# COLE SUA URL AQUI
URL_TESTE = "https://app.powerbi.com/groups/me/reports/0ab53894-c9a5-4c11-b930-89bd60f864b5/20f2ae2710e9b4e12ab0?experience=power-bi" 

diagnosticar_tela(URL_TESTE)