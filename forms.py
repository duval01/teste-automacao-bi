import requests
import random
import time

# --- CONFIGURAÇÕES ---

# 1. URL do formulário (ATENÇÃO: Troque 'viewform' por 'formResponse' no final)
# Pegue o link que você manda para as pessoas, remova tudo depois do ID e adicione /formResponse
URL_FORMULARIO = "https://docs.google.com/forms/d/e/1FAIpQLSdt6pQ7gRdbFFpXLxMtqBhExjJyr59cdgYOre8dv5UwAoKSiA/formResponse"

# 2. IDs das perguntas (Aqueles que você pegou no Passo 1)
# Substitua pelos números reais do seu formulário
CAMPO_PROJETOS = "entry.1453985706"  # ID da pergunta 1
CAMPO_SUCESSOS = "entry.1644096833"  # ID da pergunta 2
CAMPO_EU_PROF  = "entry.1903318630"  # ID da pergunta 3

# 3. Quantas respostas você quer enviar?
TOTAL_RESPOSTAS = 450

# --- BANCO DE PALAVRAS PARA VARIAR AS RESPOSTAS ---
lista_projetos = [
    "Gestão Ágil", "Inovação Digital", "Automação", "Redução de Custos", 
    "Novo CRM", "Expansão SP", "Treinamento Líderes", "Migração Nuvem",
    "Sustentabilidade", "Parceria Global", "App Mobile", "Dashboard BI"
]

lista_sucessos = [
    "Meta Batida", "Recorde Vendas", "Equipe Unida", "Escritório Novo",
    "Prêmio Inovação", "Happy Hour", "Clima Leve", "Reconhecimento",
    "Crescimento", "Aprovação Cliente", "Feedback Positivo"
]

lista_eu = [
    "Liderança", "Resiliência", "Python", "Comunicação", "Foco", 
    "Empatia", "Estratégia", "Organização", "Criatividade", 
    "Negociação", "Inteligência Emocional", "Pontualidade"
]

# --- LOOP DE ENVIO ---
print(f"🚀 Iniciando envio de {TOTAL_RESPOSTAS} respostas...")

for i in range(TOTAL_RESPOSTAS):
    # Escolhe palavras aleatórias (pode pegar 1 ou 2 para formar frases curtas)
    resp1 = f"{random.choice(lista_projetos)} {random.choice(['', random.choice(lista_projetos)])}"
    resp2 = random.choice(lista_sucessos)
    resp3 = random.choice(lista_eu)

    # Monta o pacote de dados
    dados = {
        CAMPO_PROJETOS: resp1,
        CAMPO_SUCESSOS: resp2,
        CAMPO_EU_PROF: resp3
    }

    try:
        # Envia a requisição POST (simula o clique em "Enviar")
        response = requests.post(URL_FORMULARIO, data=dados)

        if response.status_code == 200:
            print(f"[{i+1}/{TOTAL_RESPOSTAS}] Enviado com sucesso: {resp1} | {resp2}")
        else:
            print(f"⚠️ Erro no envio {i+1}: Status {response.status_code}")
    
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

    # Pausa aleatória entre 0.5 e 2 segundos para não parecer ataque hacker
    time.sleep(random.uniform(0.5, 2.0))

print("✅ Teste finalizado!")