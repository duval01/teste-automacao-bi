import asyncio
import sys
import os
import subprocess
import json
import time
import shutil
import requests
import streamlit as st
from playwright.sync_api import sync_playwright

# --- CONFIGURAÇÃO DE LOGS SIMPLES ---
def log(mensagem):
    print(f"[LOG] {mensagem}")

# --- CORREÇÃO PARA WINDOWS (DEV LOCAL) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Extrator Power BI - MG", layout="centered")

# --- 2. INSTALAÇÃO AUTOMÁTICA DO NAVEGADOR ---
@st.cache_resource
def install_playwright_browser():
    try:
        log("🚀 Verificando navegador Playwright...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        log("✅ Navegador instalado/verificado!")
    except Exception as e:
        st.error(f"Erro ao instalar navegador: {e}")

install_playwright_browser()

# --- 3. FUNÇÃO PARA CARREGAR MUNICÍPIOS ---
@st.cache_data
def carregar_municipios_mg():
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/MG/municipios"
    try:
        response = requests.get(url)
        response.raise_for_status()
        dados = response.json()
        return sorted([cidade['nome'] for cidade in dados])
    except Exception as e:
        st.error(f"Erro ao carregar municípios: {e}")
        return ["Belo Horizonte", "Contagem", "Uberlândia"]

# --- 4. LÓGICA DO PLAYWRIGHT COM DIAGNÓSTICO ---

def executar_exportacao(url_relatorio, municipio, output_folder):
    # Cria pastas necessárias
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    debug_folder = "debug_files"
    if not os.path.exists(debug_folder):
        os.makedirs(debug_folder)

    nome_arquivo = f"Relatorio_{municipio.replace(' ', '_')}.pdf"
    caminho_final = os.path.join(output_folder, nome_arquivo)
    
    # Variável para retornar o caminho da imagem de erro, se houver
    erro_screenshot = None

    # --- AUTENTICAÇÃO ---
    auth_state = None
    if "auth_file" in st.secrets and "json_content" in st.secrets["auth_file"]:
        try:
            auth_state = json.loads(st.secrets["auth_file"]["json_content"])
            log("🔑 Usando autenticação via Secrets (Cloud)")
        except Exception as e:
            return None, f"Erro ao ler Secrets: {e}", None
    elif os.path.exists("auth.json"):
        auth_state = "auth.json"
        log("💻 Usando arquivo auth.json local")
    else:
        return None, "Autenticação não encontrada.", None

    url_base_limpa = url_relatorio.split("?")[0] + "?experience=power-bi"

    try:
        with sync_playwright() as p:
            # Headless=True para servidor, False para ver rodando localmente
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            
            context = browser.new_context(
                storage_state=auth_state,
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            log(f"Acessando relatório: {url_base_limpa}")
            page.goto(url_base_limpa, timeout=60000, wait_until="domcontentloaded")
            
            # Espera inteligente pela rede (ignora se der timeout, pois PBI tem requests constantes)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                log("Networkidle excedido, continuando...")

            page.wait_for_timeout(5000) # Garantia extra para renderização

            # --- TENTATIVA DE FILTRAR MUNICÍPIO (COM SUPORTE A IFRAME) ---
            try:
                seletor_busca = "input.searchInput"
                log(f"Procurando seletor '{seletor_busca}' na página e iframes...")

                elemento_alvo = None
                
                # 1. Tenta na página principal
                if page.locator(seletor_busca).count() > 0 and page.locator(seletor_busca).first.is_visible():
                     elemento_alvo = page.locator(seletor_busca).first
                     log("Elemento encontrado no Frame Principal.")
                
                # 2. Se não achou, varre os Iframes (Comum no Power BI)
                if not elemento_alvo:
                    for frame in page.frames:
                        try:
                            if frame.locator(seletor_busca).count() > 0:
                                if frame.locator(seletor_busca).first.is_visible():
                                    elemento_alvo = frame.locator(seletor_busca).first
                                    log(f"Elemento encontrado dentro do Iframe: {frame.name or frame.url}")
                                    break
                        except:
                            continue

                if not elemento_alvo:
                    raise Exception("Input de busca não encontrado em nenhum frame.")

                # Interação
                elemento_alvo.click()
                elemento_alvo.fill("") # Limpa forçado
                elemento_alvo.fill(municipio)
                log(f"Digitado: {municipio}")
                
                page.wait_for_timeout(3000) # Espera filtrar visualmente

                # Selecionar o checkbox/texto exato
                # Nota: Se o input estava num iframe, o texto também estará. 
                # O Playwright geralmente acha texto visualmente independente do frame, mas é bom garantir.
                
                # Clicar no município (tenta encontrar o texto na página toda)
                clique_sucesso = False
                try:
                    page.get_by_text(municipio, exact=True).first.click(timeout=5000)
                    clique_sucesso = True
                except:
                    # Se falhar na página, tenta dentro do frame onde achamos o input
                    if elemento_alvo: 
                        # frame_parent é o dono do elemento_alvo
                        # Nota: element_handle não tem 'page', mas podemos usar o frame locator se salvássemos o frame.
                        # Simplificação: Tentar clicar genericamente se falhar o exact
                        pass
                
                if not clique_sucesso:
                    log("Tentando clique alternativo...")
                    page.locator(f"span[title='{municipio}']").first.click()

                log("Filtro aplicado. Aguardando renderização...")
                page.wait_for_timeout(6000) 

            except Exception as e:
                # --- CAPTURA DE DIAGNÓSTICO (ERRO NO FILTRO) ---
                log("❌ Erro ao filtrar. Gerando evidências...")
                timestamp = int(time.time())
                erro_screenshot = os.path.join(debug_folder, f"erro_filtro_{timestamp}.png")
                page.screenshot(path=erro_screenshot, full_page=True)
                
                # Salva HTML para inspeção
                with open(os.path.join(debug_folder, f"dom_erro_{timestamp}.html"), "w", encoding="utf-8") as f:
                    f.write(page.content())
                
                browser.close()
                return None, f"Erro ao filtrar município (veja imagem abaixo): {e}", erro_screenshot

            # --- EXPORTAÇÃO ---
            try:
                log("Iniciando exportação PDF...")
                # Botão Export
                page.get_by_role("button", name="Export").click()
                page.get_by_text("PDF").click()
                
                page.wait_for_selector("mat-dialog-container", timeout=20000)
                
                # Checkbox 'Current values'
                page.get_by_text("Current values", exact=True).click()

                # Download
                with page.expect_download(timeout=180000) as download_info:
                    page.locator("mat-dialog-actions").get_by_role("button", name="Export").click()
                
                download = download_info.value
                download.save_as(caminho_final)
                log("PDF salvo com sucesso.")
                
            except Exception as e:
                # --- CAPTURA DE DIAGNÓSTICO (ERRO NA EXPORTAÇÃO) ---
                timestamp = int(time.time())
                erro_screenshot = os.path.join(debug_folder, f"erro_export_{timestamp}.png")
                page.screenshot(path=erro_screenshot)
                browser.close()
                return None, f"Erro no menu de exportação: {e}", erro_screenshot

            browser.close()
            return caminho_final, "Sucesso", None

    except Exception as e:
        return None, f"Erro geral no Playwright: {e}", None

# --- 5. INTERFACE DO STREAMLIT ---

st.title("📊 Exportador de Relatórios Power BI")
st.caption("Com diagnósticos automáticos de erro")
st.markdown("---")

lista_cidades = carregar_municipios_mg()
municipio_selecionado = st.selectbox(
    "Selecione o Município:",
    options=lista_cidades,
    placeholder="Digite para pesquisar..."
)

# AJUSTE AQUI A URL
URL_BASE = "https://app.powerbi.com/groups/me/reports/848d470e-c20f-4948-8ab3-8223d80eed5a?experience=power-bi"
PASTA_TEMP = "temp_pdfs"

if st.button("Gerar PDF", type="primary"):
    if not municipio_selecionado:
        st.warning("Por favor, selecione um município.")
    else:
        status_box = st.status(f"Processando **{municipio_selecionado}**...", expanded=True)
        
        with status_box:
            st.write("🤖 Inicializando robô...")
            # Chama a função
            caminho_arquivo, mensagem, img_erro = executar_exportacao(URL_BASE, municipio_selecionado, PASTA_TEMP)
            
            if caminho_arquivo:
                st.write("📄 PDF gerado!")
                status_box.update(label="Processo concluído!", state="complete", expanded=False)
                
                with open(caminho_arquivo, "rb") as arquivo:
                    st.download_button(
                        label=f"📥 Baixar PDF de {municipio_selecionado}",
                        data=arquivo,
                        file_name=os.path.basename(caminho_arquivo),
                        mime="application/pdf"
                    )
            else:
                status_box.update(label="Falha no processo", state="error", expanded=True)
                st.error(f"❌ {mensagem}")
                
                # MOSTRA O SCREENSHOT DO ERRO NA TELA
                if img_erro and os.path.exists(img_erro):
                    st.warning("📸 Screenshot do momento do erro:")
                    st.image(img_erro, caption="O que o robô estava vendo quando falhou", use_container_width=True)
                    
                    # Opcional: Ler o HTML se quiser (normalmente só imagem basta)
                    # st.download_button("Baixar HTML de Debug", ...)
