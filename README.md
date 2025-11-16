App de Análise Orçamentária (v4.0 com IA)

Este é um aplicativo Streamlit que analisa os dados brutos da Dívida Pública e dos Gastos Orçamentários do Brasil, usando pandas-ai e a API do Google Gemini para interatividade em linguagem natural.

🚀 Como Fazer o Deploy (Passo a Passo)

Você precisa de 5 arquivos no seu repositório do GitHub:

app_divida_publica_v4.py (O código do app)

requirements.txt (As bibliotecas)

divida_estoque_historico.csv (Seu dataset da Dívida)

gastos_orcamento_2025.csv (Seu dataset de Gastos)

README.md (Este arquivo)

Passo 1: Obter sua Chave de API do Gemini (Google AI)

O aplicativo precisa de uma chave de API para funcionar.

Vá para o Google AI Studio: https://aistudio.google.com/app

Faça login com sua conta do Google.

No menu à esquerda, clique em "Get API key".

Clique em "Create API key in new project".

Copie a chave gerada (ex: AIza...). Guarde-a em segurança.

Passo 2: Fazer o Deploy no Streamlit Cloud

Faça o upload dos 5 arquivos para o seu repositório no GitHub.

Vá para o Streamlit Cloud e crie uma conta (faça login com o GitHub).

Clique em "New app".

Selecione seu repositório, a branch main, e o arquivo principal app_divida_publica_v4.py.

Clique em "Deploy!".

Passo 3 (CRÍTICO): Configurar os "Secrets"

O aplicativo vai "quebrar" na primeira vez, mostrando um aviso sobre a API Key. Isso é esperado.

No painel do seu aplicativo no Streamlit Cloud, clique no menu "Manage app" (Gerenciar app) no canto inferior direito.

No menu que se abre, clique em "Secrets" (Segredos).

No campo de texto, cole o seguinte:

GOOGLE_API_KEY = "SUA_CHAVE_DE_API_QUE_VOCE_COPIOU_AQUI"


Troque a parte SUA_CHAVE_DE_API... pela chave real que você copiou no Passo 1.

Clique em "Save" (Salvar).

O Streamlit vai pedir para "Reboot" (Reiniciar) o aplicativo. Aceite.

Pronto! Após reiniciar, o aplicativo encontrará a chave no "Secrets" e a aba "Chat com IA" funcionará perfeitamente.