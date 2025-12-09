from playwright.sync_api import sync_playwright

def gerar_sessao():
    with sync_playwright() as p:
        # Abre o navegador visível (headless=False) para você interagir
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("--- INICIANDO PROCESSO DE LOGIN ---")
        print("1. O navegador vai abrir.")
        print("2. Faça login na sua conta Microsoft.")
        print("3. Marque 'Sim' para continuar conectado.")
        print("4. Aguarde até que a página inicial do Power BI carregue totalmente.")
        
        # Acessa a página de login
        page.goto("https://app.powerbi.com/home")

        # O script pausa aqui e espera você dar o comando no terminal
        input(">>> DEPOIS que você estiver logado e vendo o Power BI, pressione ENTER aqui no terminal para salvar... <<<")

        # Salva os cookies e o estado da sessão no arquivo
        context.storage_state(path="auth.json")
        print("Sucesso! Arquivo 'auth.json' gerado.")
        
        browser.close()

if __name__ == "__main__":
    gerar_sessao()