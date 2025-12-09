import asyncio
import sys
import os
import subprocess
import json
import urllib.parse
import requests
import streamlit as st
from playwright.sync_api import sync_playwright

# --- CORREÇÃO PARA WINDOWS (DEV LOCAL) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Extrator Power BI - MG", layout="centered")

# --- 2. INSTALAÇÃO AUTOMÁTICA DO NAVEGADOR (FIX PARA CLOUD) ---
@st.cache_resource
def install_playwright_browser():
    """Instala o navegador Chromium na primeira execução do app."""
    try:
        # Verifica se já existe ou tenta instalar
        print("🚀 Verificando navegador Playwright...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Navegador instalado/verificado!")
    except Exception as e:
        st.error(f"Erro ao instalar navegador: {e}")

# Executa a instalação antes de qualquer coisa
install_playwright_browser()

# --- 3. FUNÇÃO PARA CARREGAR MUNICÍPIOS (CACHEADA) ---
@st.cache_data
def carregar_municipios_mg():
    """Busca a lista de municípios de MG na API do IBGE."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/MG/municipios"
    try:
        response = requests.get(url)
        response.raise_for_status()
        dados = response.json()
        return sorted([cidade['nome'] for cidade in dados])
    except Exception as e:
        st.error(f"Erro ao carregar municípios: {e}")
        return ["Belo Horizonte", "Contagem", "Uberlândia"]

# --- 4. LÓGICA DO PLAYWRIGHT ---

def executar_exportacao(url_relatorio, municipio, output_folder):
    nome_arquivo = f"Relatorio_{municipio.replace(' ', '_')}.pdf"
    caminho_final = os.path.join(output_folder, nome_arquivo)
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # --- LÓGICA DE AUTENTICAÇÃO HÍBRIDA ---
    # 1. Tenta ler do st.secrets (Nuvem)
    # 2. Se falhar, tenta ler o arquivo físico auth.json (Local)
    auth_state = None
    
    if "auth_file" in st.secrets and "json_content" in st.secrets["auth_file"]:
        try:
            # Carrega o JSON que está dentro da string no TOML
            auth_state = json.loads(st.secrets["auth_file"]["json_content"])
            print("🔑 Usando autenticação via Secrets (Cloud)")
        except Exception as e:
            return None, f"Erro ao ler Secrets: {e}"
    elif os.path.exists("auth.json"):
        auth_state = "auth.json"
        print("💻 Usando arquivo auth.json local")
    else:
        return None, "Autenticação não encontrada. Configure o secrets.toml ou suba o auth.json (apenas local)."

    # Limpa a URL para garantir que o robô faça o filtro manual na UI
    url_base_limpa = url_relatorio.split("?")[0] + "?experience=power-bi"

    try:
        with sync_playwright() as p:
            # Headless=True é obrigatório no Cloud. Mude para False apenas para testar localmente.
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            
            # Cria o contexto com a autenticação carregada
            context = browser.new_context(
                storage_state=auth_state,
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            # 1. Abre o relatório
            page.goto(url_base_limpa, timeout=60000, wait_until="domcontentloaded")
            
            # Dica: Esperar um pouco mais para garantir que o Power BI carregou os scripts
            page.wait_for_timeout(5000)

            # 2. Resetar Filtros (Se existir)
            try:
                botao_reset = page.get_by_role("button", name="Redefinir para o padrão")
                if botao_reset.is_visible():
                    botao_reset.click()
                    page.wait_for_timeout(2000)
            except:
                pass

            # 3. Interage com a Busca de Município
            # Localiza o input de busca (lupinha)
            try:
                campo_busca = page.locator("input.searchInput")
                campo_busca.wait_for(state="visible", timeout=30000)
                
                campo_busca.click()
                campo_busca.clear()
                campo_busca.fill(municipio)
                page.wait_for_timeout(2000) # Espera filtrar a lista
                
                # 4. Clica na cidade correta
                # Ajuste: Às vezes o Power BI precisa de um clique específico no checkbox ou no texto
                # O 'exact=True' ajuda a não clicar em "Belo Horizonte do Sul" quando procura "Belo Horizonte"
                page.get_by_text(municipio, exact=True).first.click()
                
                # Espera o relatório renderizar os dados da cidade
                # Aumente este tempo se o relatório for pesado
                page.wait_for_timeout(6000) 

            except Exception as e:
                browser.close()
                return None, f"Erro ao filtrar município: {e}"

            # --- Exportação ---
            try:
                botao_exportar = page.get_by_role("button", name="Export")
                if not botao_exportar.is_visible():
                     # Tenta achar pelo menu 'Arquivo' se o botão direto não estiver lá
                     pass 
                
                botao_exportar.click()
                
                menu_pdf = page.get_by_text("PDF")
                if not menu_pdf.is_visible(): page.wait_for_timeout(1000)
                menu_pdf.click()
                
                page.wait_for_selector("mat-dialog-container", timeout=20000)
                
                # Garante que vai exportar o que estamos vendo
                page.get_by_text("Current values", exact=True).click()

                with page.expect_download(timeout=180000) as download_info:
                    page.locator("mat-dialog-actions").get_by_role("button", name="Export").click()
                    
                download = download_info.value
                download.save_as(caminho_final)
                
            except Exception as e:
                browser.close()
                return None, f"Erro no menu de exportação: {e}"

            browser.close()
            return caminho_final, "Sucesso"

    except Exception as e:
        return None, f"Erro geral no Playwright: {e}"

# --- 5. INTERFACE DO STREAMLIT ---

st.title("📊 Exportador de Relatórios Power BI")
st.markdown("---")

# Seleção
lista_cidades = carregar_municipios_mg()
municipio_selecionado = st.selectbox(
    "Selecione o Município:",
    options=lista_cidades,
    placeholder="Digite para pesquisar..."
)

# Configuração
URL_BASE = "https://app.powerbi.com/groups/me/reports/848d470e-c20f-4948-8ab3-8223d80eed5a?experience=power-bi"
PASTA_TEMP = "temp_pdfs"

if st.button("Gerar PDF", type="primary"):
    if not municipio_selecionado:
        st.warning("Por favor, selecione um município.")
    else:
        status_text = st.empty()
        
        with st.spinner(f"Iniciando robô para **{municipio_selecionado}**..."):
            # Chama a função. Note que removemos a lógica de url_teste filtrada antes
            # pois o robô vai digitar o filtro manualmente lá dentro.
            caminho_arquivo, mensagem = executar_exportacao(URL_BASE, municipio_selecionado, PASTA_TEMP)
        
        if caminho_arquivo:
            status_text.success("✅ Relatório gerado com sucesso!")
            
            with open(caminho_arquivo, "rb") as arquivo:
                st.download_button(
                    label=f"📥 Baixar PDF de {municipio_selecionado}",
                    data=arquivo,
                    file_name=os.path.basename(caminho_arquivo),
                    mime="application/pdf"
                )
        else:
            status_text.error(f"❌ Falha na exportação: {mensagem}")
