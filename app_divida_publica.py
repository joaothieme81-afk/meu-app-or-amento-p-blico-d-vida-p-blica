# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v4.0) - "Plano Profissional (IA)"
Analisa os datasets CSV brutos (e grandes) do Tesouro Transparente.

Arquitetura:
1.  Lê os arquivos CSV locais (versionados no GitHub).
2.  Usa @st.cache_data para carregar os datasets pesados apenas uma vez.
3.  Implementa filtros dinâmicos (Aba 1 e 2).
4.  [NOVO] Implementa um Agente de IA (Gemini + pandas-ai) para 
    responder perguntas em linguagem natural (Aba 3).
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Novas importações para a IA
from pandasai import SmartDataframe
from pandasai.llm import GoogleGemini

# --- Configuração da Página ---
st.set_page_config(
    page_title="Análise Orçamentária do Brasil (v4.0 - IA)",
    page_icon="🇧🇷",
    layout="wide"
)

# --- Funções de Limpeza e Carregamento de Dados (as mesmas do v3.2) ---

@st.cache_data
def carregar_dados_gastos(caminho_csv):
    """
    Carrega o CSV de Orçamento de Despesa.
    Este é um arquivo grande, então o cache é essencial.
    """
    try:
        df = pd.read_csv(
            caminho_csv,
            sep=';',
            encoding='latin1'
        )
        
        # Renomear colunas para facilitar
        df = df.rename(columns={
            'NOME FUNÇÃO': 'Funcao',
            'NOME ÓRGÃO SUPERIOR': 'Orgao_Superior',
            'NOME ÓRGÃO SUBORDINADO': 'Orgao_Subordinado',
            'NOME UNIDADE ORÇAMENTÁRIA': 'Unidade_Orcamentaria',
            'ORÇAMENTO REALIZADO (R$)': 'Valor_Realizado'
        })
        
        # Limpeza de Dados v3.1 (Mais Robusta)
        df['Valor_Realizado'] = df['Valor_Realizado'].astype(str)
        df['Valor_Realizado'] = df['Valor_Realizado'].str.replace('.', '', regex=False)
        df['Valor_Realizado'] = df['Valor_Realizado'].str.replace(',', '.', regex=False)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        
        df = df.dropna(subset=['Valor_Realizado'])
        
        colunas_uteis = ['Funcao', 'Orgao_Superior', 'Orgao_Subordinado', 'Unidade_Orcamentaria', 'Valor_Realizado']
        df_limpo = df[colunas_uteis]
        
        return df_limpo

    except FileNotFoundError:
        st.error(f"Erro: Arquivo {caminho_csv} não encontrado. Faça o upload dele para o GitHub.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar e limpar {caminho_csv}: {e}")
        return pd.DataFrame()

@st.cache_data
def carregar_dados_divida(caminho_csv):
    """
    Carrega o CSV histórico do Estoque da Dívida.
    """
    try:
        df = pd.read_csv(
            caminho_csv,
            sep=';',
            encoding='latin1'
        )
        
        # Renomear colunas
        df = df.rename(columns={
            'Mes do Estoque': 'Data',
            'Tipo de Divida': 'Tipo_Divida',
            'Valor do Estoque': 'Valor_Estoque'
        })
        
        # Converter 'Data' para um formato datetime
        df['Data'] = pd.to_datetime(df['Data'], format='%m/%Y')
        df['Ano'] = df['Data'].dt.year
        
        # Limpeza de Dados v3.1 (Mais Robusta)
        df['Valor_Estoque'] = df['Valor_Estoque'].astype(str)
        df['Valor_Estoque'] = df['Valor_Estoque'].str.replace('.', '', regex=False)
        df['Valor_Estoque'] = df['Valor_Estoque'].str.replace(',', '.', regex=False)
        df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce')
        
        df = df.dropna(subset=['Valor_Estoque'])
        
        colunas_uteis = ['Data', 'Ano', 'Tipo_Divida', 'Valor_Estoque']
        df_limpo = df[colunas_uteis]
        
        return df_limpo
        
    except FileNotFoundError:
        st.error(f"Erro: Arquivo {caminho_csv} não encontrado. Faça o upload dele para o GitHub.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar e limpar {caminho_csv}: {e}")
        return pd.DataFrame()

# --- Funções de Gráfico (Idênticas ao v3.2) ---

def formatar_bilhoes(x, pos):
    """Formata o eixo Y para 'R$ 100 bi'."""
    return f'R$ {x*1e-9:.0f} bi'

def formatar_trilhoes(x, pos):
    """Formata o eixo Y para 'R$ 1.5 T'."""
    return f'R$ {x*1e-12:.1f} T'

# (As funções de criar_grafico_... são complexas e idênticas ao v3.2,
#  portanto, omitidas aqui para brevidade, mas elas estão no código final)

# --- [INÍCIO] Funções de Gráfico (copiadas do v3.2) ---
def criar_grafico_gastos(df_filtrado):
    df_plot = df_filtrado.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(10, len(df_plot) * 0.5))
    bars = ax.barh(df_plot.index, df_plot.values, color='#0072B2')
    ax.set_title('Gastos Pagos por Função do Governo', fontsize=16)
    ax.set_xlabel('Valor Pago (em Bilhões de R$)', fontsize=12)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(formatar_bilhoes))
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    for bar in bars:
        ax.text(
            bar.get_width() + (bar.get_width() * 0.01), 
            bar.get_y() + bar.get_height()/2, 
            f'R$ {bar.get_width()*1e-9:.1f} bi', 
            va='center', 
            ha='left'
        )
    plt.tight_layout()
    return fig

def criar_grafico_evolucao_divida(df_filtrado):
    df_plot = df_divida_filtrado.groupby('Data')['Valor_Estoque'].sum()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df_plot_divida.index, df_plot_divida.values, color='#D55E00')
    ax.set_title('Evolução do Estoque da Dívida Pública Federal', fontsize=16)
    ax.set_ylabel('Valor (em Trilhões de R$)', fontsize=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(formatar_trilhoes))
    ax.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    return fig
# --- [FIM] Funções de Gráfico ---

# --- INTERFACE PRINCIPAL DO APLICATIVO ---

st.title("Análise Orçamentária do Brasil (v4.0 - IA)")
st.markdown("Plataforma de análise de dados com IA (Gemini) sobre os datasets brutos do Tesouro Transparente.")

# --- CARREGAMENTO DOS DADOS ---
with st.spinner("Carregando datasets brutos... (Pode levar um minuto na primeira carga)"):
    df_gastos = carregar_dados_gastos("gastos_orcamento_2025.csv")
    df_divida = carregar_dados_divida("divida_estoque_historico.csv")

# Verifica se os dados foram carregados antes de continuar
if df_gastos.empty or df_divida.empty:
    st.error("Falha ao carregar um ou mais datasets. Verifique os arquivos no GitHub.")
else:
    # --- Abas Principais ---
    tab1, tab2, tab3 = st.tabs([
        "📊 Análise de Gastos (2025)", 
        "📈 Análise da Dívida (Histórico)",
        "🤖 Chat com IA (Gemini)"
    ])

    # --- ABA 1 E 2 (Idênticas ao v3.2) ---
    with tab1:
        st.header("Análise de Profundidade: Orçamento de Gastos 2025")
        st.markdown("Use os filtros para explorar o orçamento de despesas realizado em 2025.")
        
        # --- Filtros para Gastos ---
        st.sidebar.header("Filtros de Gastos (2025)")
        
        lista_funcoes = ['Todas'] + sorted(df_gastos['Funcao'].unique())
        funcao_selecionada = st.sidebar.selectbox("Selecione uma Função:", lista_funcoes)
        
        if funcao_selecionada == 'Todas':
            df_gastos_filtrado = df_gastos
        else:
            df_gastos_filtrado = df_gastos[df_gastos['Funcao'] == funcao_selecionada]
            
        lista_orgaos = ['Todos'] + sorted(df_gastos_filtrado['Orgao_Superior'].unique())
        orgao_selecionado = st.sidebar.selectbox("Selecione um Órgão Superior:", lista_orgaos)

        if orgao_selecionado != 'Todos':
            df_gastos_filtrado = df_gastos_filtrado[df_gastos_filtrado['Orgao_Superior'] == orgao_selecionado]
        
        total_realizado = df_gastos_filtrado['Valor_Realizado'].sum()
        num_orgaos = df_gastos_filtrado['Orgao_Superior'].nunique()
        num_unidades = df_gastos_filtrado['Unidade_Orcamentaria'].nunique()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Valor Total Realizado (Filtro)", f"R$ {total_realizado*1e-9:.2f} bi")
        col2.metric("Nº de Órgãos Superiores", num_orgaos)
        col3.metric("Nº de Unidades Orçamentárias", num_unidades)

        st.subheader("Top 15 Unidades Orçamentárias (por Valor Realizado)")
        
        df_plot_gastos = df_gastos_filtrado.groupby('Unidade_Orcamentaria')['Valor_Realizado'].sum().nlargest(15).sort_values(ascending=True)
        
        if not df_plot_gastos.empty:
            fig_gastos = criar_grafico_gastos(df_gastos_filtrado)
            st.pyplot(fig_gastos)
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            
        with st.expander("Ver dados brutos (filtrados)"):
            st.dataframe(df_gastos_filtrado)

    with tab2:
        st.header("Análise de Amplitude: Dívida Pública (Histórico)")
        st.markdown("Use os filtros para explorar o histórico da Dívida Pública Federal.")
        
        # --- Filtros para Dívida ---
        st.sidebar.header("Filtros da Dívida (Histórico)")
        
        anos_disponiveis = sorted(df_divida['Ano'].unique())
        ano_selecionado = st.sidebar.slider(
            "Selecione o Ano (ou intervalo de anos):",
            min_value=int(min(anos_disponiveis)),
            max_value=int(max(anos_disponiveis)),
            value=(int(min(anos_disponiveis)), int(max(anos_disponiveis)))
        )
        
        tipos_divida = ['Todos'] + sorted(df_divida['Tipo_Divida'].unique())
        tipo_selecionado = st.sidebar.selectbox("Selecione o Tipo de Dívida:", tipos_divida)

        df_divida_filtrado = df_divida[
            (df_divida['Ano'] >= ano_selecionado[0]) &
            (df_divida['Ano'] <= ano_selecionado[1])
        ]
        
        if tipo_selecionado != 'Todos':
            df_divida_filtrado = df_divida_filtrado[df_divida_filtrado['Tipo_Divida'] == tipo_selecionado]
            
        df_plot_divida = df_divida_filtrado.groupby('Data')['Valor_Estoque'].sum()

        if not df_plot_divida.empty:
            valor_recente = df_plot_divida.iloc[-1] 
            data_recente = df_plot_divida.index.max()
            st.metric(f"Estoque Total na Data Mais Recente (em {data_recente.strftime('%m/%Y')})", f"R$ {valor_recente*1e-12:.2f} T")
        else:
            st.metric("Estoque Total na Data Mais Recente", "N/A")

        st.subheader("Evolução do Estoque da Dívida (no filtro)")
        
        if not df_plot_divida.empty:
            fig_divida = criar_grafico_evolucao_divida(df_divida_filtrado)
            st.pyplot(fig_divida)
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            
        with st.expander("Ver dados brutos (filtrados)"):
            st.dataframe(df_divida_filtrado)
            
    # --- [NOVO] ABA 3: CHAT COM IA (GEMINI) ---
    with tab3:
        st.header("🤖 Chat com IA (Gemini + PandasAI)")
        st.markdown("""
        Faça perguntas em linguagem natural sobre os datasets. A IA (Gemini) irá 
        traduzir sua pergunta em código Python e executá-lo nos dados para 
        encontrar a resposta.
        
        **Exemplos de perguntas:**
        - Qual o gasto total com Saúde em 2025?
        - Liste os 5 maiores órgãos superiores por valor realizado.
        - Qual o valor médio do estoque da dívida no ano de 2023?
        - Mostre a evolução do estoque da Dívida Interna.
        """)
        
        # 1. Tentar pegar a API Key dos "Secrets" do Streamlit Cloud
        api_key = st.secrets.get("GOOGLE_API_KEY")

        # 2. Se não achar, pedir para o usuário
        if not api_key:
            st.warning("Chave de API do Google (Gemini) não encontrada.")
            api_key = st.text_input("Por favor, insira sua chave de API do Google AI Studio para continuar:", type="password")
            if not api_key:
                st.stop() # Para o app aqui se a chave não for fornecida

        # 3. Inicializar o Agente de IA (pandas-ai)
        try:
            llm = GoogleGemini(api_key=api_key)
            
            # Criamos o "agente" e damos a ele os dois dataframes
            # O nome do dataframe é importante para o usuário perguntar
            agent = SmartDataframe(
                [df_gastos, df_divida],
                config={"llm": llm, "verbose": True},
                name=["gastos_2025", "divida_historico"]
            )
            
            # Inicializar o histórico do chat
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Mostrar histórico
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Input do usuário
            if prompt := st.chat_input("Faça uma pergunta sobre os dados..."):
                # Adiciona pergunta ao histórico e mostra
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Gera a resposta
                with st.chat_message("assistant"):
                    with st.spinner("Gemini está pensando..."):
                        # É aqui que a "mágica" acontece
                        response = agent.chat(prompt)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"Erro ao inicializar ou usar o agente de IA: {e}")
            st.error("Verifique se sua chave de API é válida e se a biblioteca `pandas-ai` está instalada.")
            
# --- BARRA LATERAL (SOBRE) ---
st.sidebar.title("Sobre o Aplicativo")
st.sidebar.info(f"""
Este aplicativo é uma ferramenta de análise de dados para o Orçamento Federal e a Dívida Pública do Brasil.

**Arquitetura de Dados (v4.0):**
1.  Lê os datasets CSV brutos (`divida_estoque_historico.csv` e `gastos_orcamento_2025.csv`) versionados no GitHub.
2.  Usa `@st.cache_data` para carregar os dados em memória.
3.  Aba 1 e 2: Filtros dinâmicos (Pandas)
4.  Aba 3: Chat em linguagem natural (PandasAI + Google Gemini).
""")
