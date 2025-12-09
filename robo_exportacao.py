from playwright.sync_api import sync_playwright
import os

def exportacao_oculta_fix(report_url, output_path):
    print(f"--- Iniciando Exportação Headless (1920x1080) ---")
    
    if not os.path.exists("auth.json"):
        print("ERRO: auth.json não encontrado.")
        return

    with sync_playwright() as p:
        print("1. Inicializando motor...")
        # args=["--start-maximized"] ajuda em alguns casos, mas o viewport é o principal
        browser = p.chromium.launch(headless=True) 
        
        # --- AQUI ESTÁ A CORREÇÃO ---
        # Definimos explicitamente uma tela grande para o Power BI mostrar todos os botões
        context = browser.new_context(
            storage_state="auth.json",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        print(f"2. Acessando relatório...")
        page.goto(report_url)
        
        try:
            print("Aguardando carregamento da interface...")
            
            # Encontra o botão Exportar
            botao_exportar = page.get_by_role("button", name="Export")
            botao_exportar.wait_for(state="visible", timeout=60000)
            
            print("Botão encontrado! Clicando...")
            botao_exportar.click()

            # Selecionar PDF
            page.get_by_text("PDF").click()
            
            # Aguardar Pop-up
            page.wait_for_selector("mat-dialog-container", timeout=20000)

            # Selecionar 'Valores atuais'
            page.get_by_text("Current values").click()

            print("Enviando pedido de exportação...")
            
            with page.expect_download(timeout=180000) as download_info:
                page.locator("mat-dialog-actions").get_by_role("button", name="Export").click()
                
            download = download_info.value
            download.save_as(output_path)
            print(f"SUCESSO! Arquivo salvo em: {os.path.abspath(output_path)}")

        except Exception as e:
            print(f"\n--- ERRO ---")
            print(f"Detalhe: {e}")
            # Tira um print para vermos como a tela estava "olhando" para o robô
            page.screenshot(path="erro_headless_fullhd.png")
            print("Verifique a imagem 'erro_headless_fullhd.png' para ver o que o robô viu.")

        finally:
            browser.close()

# --- CONFIGURAÇÃO ---
URL_RELATORIO = "https://app.powerbi.com/groups/me/reports/645219ca-d616-4502-b700-4a01bd97d3d8/e73c054d1bbe2b20dadf?experience=power-bi" 
NOME_ARQUIVO = "Relatorio_Final_Headless.pdf"

exportacao_oculta_fix(URL_RELATORIO, NOME_ARQUIVO)