import asyncio
import sys

# --- CORREÇÃO PARA WINDOWS (CRUCIAL PARA O PLAYWRIGHT) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ---------------------------------------------------------

import streamlit as st
from playwright.sync_api import sync_playwright
import urllib.parse
import os
import requests

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Extrator Power BI - MG", layout="centered")

# --- 2. FUNÇÃO PARA CARREGAR MUNICÍPIOS (CACHEADA) ---
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

# --- 3. LÓGICA DE URL E PLAYWRIGHT ---
def gerar_url_filtrada(base_url, filtros):
    if not filtros: return base_url
    
    partes_filtro = []
    for tabela, colunas in filtros.items():
        tabela_safe = tabela.replace(" ", "_x0020_")
        for coluna, valor in colunas.items():
            coluna_safe = coluna.replace(" ", "_x0020_")
            # Trata apóstrofos (Ex: Pau d'Arco -> Pau d''Arco)
            valor_escapado = valor.replace("'", "''") 
            valor_final = f"'{valor_escapado}'"
            partes_filtro.append(f"{tabela_safe}/{coluna_safe} eq {valor_final}")

    query_string = " and ".join(partes_filtro)
    separador = "&" if "?" in base_url else "?"
    
    return f"{base_url}{separador}filter={urllib.parse.quote(query_string)}"

def executar_exportacao(url_relatorio, municipio, output_folder, auth_file="auth.json"):
    nome_arquivo = f"Relatorio_{municipio.replace(' ', '_')}.pdf"
    caminho_final = os.path.join(output_folder, nome_arquivo)
    
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    
    # URL Limpa (sem ?filter=...) para evitar conflitos.
    # Vamos deixar o robô fazer o trabalho sujo.
    url_base_limpa = url_relatorio.split("?")[0] + "?experience=power-bi"

    try:
        with sync_playwright() as p:
            # DICA: Use headless=False na primeira vez para VER ele trabalhando
            browser = p.chromium.launch(headless=False) 
            context = browser.new_context(
                storage_state=auth_file,
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            # 1. Abre o relatório original (com o filtro que estiver salvo lá)
            page.goto(url_base_limpa, timeout=60000, wait_until="networkidle")
            
            # 2. (Opcional) Clica no botão "Redefinir Filtros" do Power BI
            # Isso garante que o relatório comece limpo. 
            # O seletor abaixo busca o botão de "Reset" na barra superior (pode variar)
            try:
                # Tenta clicar no botão de reset se ele existir e estiver visível
                botao_reset = page.get_by_role("button", name="Redefinir para o padrão")
                if botao_reset.is_visible():
                    botao_reset.click()
                    page.wait_for_timeout(2000)
            except:
                pass # Se não achar o botão, segue a vida

            # 3. Interage com a Busca de Município
            # Localiza o input de busca (lupinha)
            campo_busca = page.locator("input.searchInput")
            campo_busca.wait_for(state="visible", timeout=30000)
            
            # Limpa o que estiver escrito e digita o novo
            campo_busca.click()
            campo_busca.clear() 
            campo_busca.fill(municipio)
            
            # Espera a lista atualizar
            page.wait_for_timeout(2000)
            
            # 4. Clica na cidade correta
            # O seletor 'div[role="radio"]' ou busca por texto costuma funcionar bem
            # Procura pelo texto exato do município dentro do visual
            page.get_by_text(municipio, exact=True).click()
            
            # Espera o relatório renderizar os dados da cidade
            page.wait_for_timeout(5000)

            # --- Exportação (igual ao anterior) ---
            botao_exportar = page.get_by_role("button", name="Exportar")
            botao_exportar.click()
            
            menu_pdf = page.get_by_text("PDF")
            if not menu_pdf.is_visible(): page.wait_for_timeout(1000)
            menu_pdf.click()
            
            page.wait_for_selector("mat-dialog-container", timeout=20000)
            
            # IMPORTANTE: Current Values
            page.get_by_text("Valores atuais", exact=False).click()

            with page.expect_download(timeout=180000) as download_info:
                page.locator("mat-dialog-actions").get_by_role("button", name="Exportar").click()
                
            download = download_info.value
            download.save_as(caminho_final)
            browser.close()
            
            return caminho_final, "Sucesso"

    except Exception as e:
        return None, str(e)

# --- 4. INTERFACE DO STREAMLIT ---

st.title("📊 Exportador de Relatórios Power BI")
st.markdown("---")

# Seleção
lista_cidades = carregar_municipios_mg()
municipio_selecionado = st.selectbox(
    "Selecione o Município:",
    options=lista_cidades,
    placeholder="Digite para pesquisar..."
)

# --- CONFIGURAÇÃO (AJUSTE AQUI SE NECESSÁRIO) ---
URL_BASE = "https://app.powerbi.com/groups/me/reports/848d470e-c20f-4948-8ab3-8223d80eed5a?experience=power-bi"
PASTA_TEMP = "temp_pdfs"

# Botão de Ação
if st.button("Gerar PDF", type="primary"):
    if not municipio_selecionado:
        st.warning("Por favor, selecione um município.")
    else:
        # --- DEBUG DA URL: MOSTRA O LINK NA TELA ---
        
        # 1. Definição do Filtro (VERIFIQUE SE OS NOMES BATEM COM SEU PBI)
        # Tente usar .upper() se sua base for toda maiúscula: municipio_selecionado.upper()
        meus_filtros = {
            'Municipios': {'Municipio': municipio_selecionado}
        }
        
        # 2. Gera a URL para teste
        url_teste = gerar_url_filtrada(URL_BASE, meus_filtros)
        
        # 3. Exibe na tela para validação
        st.info("🔎 **Modo Debug:** Clique no link abaixo para verificar se o Power BI filtra corretamente:")
        st.markdown(f"[🔗 Abrir Relatório Filtrado ({municipio_selecionado})]({url_teste})", unsafe_allow_html=True)
        st.caption(f"URL Gerada: `{url_teste}`")
        
        st.markdown("---")
        
        # --- INÍCIO DA EXPORTAÇÃO ---
        status_text = st.empty()
        
        with st.spinner(f"Processando **{municipio_selecionado}**... (Isso leva ~30s)"):
            # Passamos a url_teste que já está filtrada
            caminho_arquivo, mensagem = executar_exportacao(url_teste, municipio_selecionado, PASTA_TEMP)
        
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