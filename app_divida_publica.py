# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v3.0) - "Plano Profissional"
Analisa os datasets CSV brutos (e grandes) do Tesouro Transparente.

Arquitetura:
1.  Lê os arquivos CSV locais (versionados no GitHub) `divida_estoque_historico.csv` 
    e `gastos_orcamento_2025.csv`.
2.  Usa @st.cache_data para carregar os datasets pesados apenas uma vez.
3.  Implementa filtros dinâmicos (interatividade "sofisticada").
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# --- Configuração da Página ---
st.set_page_config(
    page_title="Análise Orçamentária do Brasil (v3.0)",
    page_icon="🇧🇷",
    layout="wide"
)

# --- Funções de Limpeza e Carregamento de Dados ---

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
            encoding='latin1',
            decimal=',',  # Define a vírgula como separador decimal
            thousands='.' # Define o ponto como separador de milhar
        )
        
        # Limpar os dados de valor (converter de R$ 1.234,56 para 1234.56)
        # Usamos .replace() para remover 'R$ ' e '.' dos milhares
        # Usamos .str.replace() para trocar ',' por '.' (decimal)
        # Usamos pd.to_numeric() para converter para número
        
        # Vamos usar a coluna 'ORÇAMENTO REALIZADO (R$)'
        # Renomear colunas para facilitar
        df = df.rename(columns={
            'NOME FUNÇÃO': 'Funcao',
            'NOME ÓRGÃO SUPERIOR': 'Orgao_Superior',
            'NOME ÓRGÃO SUBORDINADO': 'Orgao_Subordinado',
            'NOME UNIDADE ORÇAMENTÁRIA': 'Unidade_Orcamentaria',
            'ORÇAMENTO REALIZADO (R$)': 'Valor_Realizado'
        })
        
        # Converte a coluna de valor para numérico.
        # Erros 'coerce' transforma qualquer valor que não seja número em NaN (Nulo)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        
        # Remove linhas onde o valor não pôde ser convertido
        df = df.dropna(subset=['Valor_Realizado'])
        
        # Seleciona apenas as colunas que vamos usar
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
            encoding='latin1',
            decimal=',',
            thousands='.'
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
        
        # Converter 'Valor_Estoque' para numérico
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

# --- Funções de Gráfico ---

def formatar_bilhoes(x, pos):
    """Formata o eixo Y para 'R$ 100 bi'."""
    return f'R$ {x*1e-9:.0f} bi'

def formatar_trilhoes(x, pos):
    """Formata o eixo Y para 'R$ 1.5 T'."""
    return f'R$ {x*1e-12:.1f} T'

# --- Interface Principal ---

st.title("Análise Orçamentária do Brasil (v3.0 - Pro)")
st.markdown("Plataforma de análise dinâmica dos datasets brutos do Tesouro Transparente.")

# Carrega os dados (com cache)
with st.spinner("Carregando datasets brutos... (Pode levar um minuto na primeira carga)"):
    df_gastos = carregar_dados_gastos("gastos_orcamento_2025.csv")
    df_divida = carregar_dados_divida("divida_estoque_historico.csv")

# Verifica se os dados foram carregados antes de continuar
if df_gastos.empty or df_divida.empty:
    st.error("Falha ao carregar um ou mais datasets. Verifique os arquivos no GitHub.")
else:
    # --- Abas Principais ---
    tab1, tab2 = st.tabs(["📊 Análise de Gastos (2025)", "📈 Análise da Dívida (Histórico)"])

    # --- ABA 1: ANÁLISE DE GASTOS (PROFUNDIDADE) ---
    with tab1:
        st.header("Análise de Profundidade: Orçamento de Gastos 2025")
        st.markdown("Use os filtros para explorar o orçamento de despesas realizado em 2025.")
        
        # --- Filtros para Gastos ---
        st.sidebar.header("Filtros de Gastos (2025)")
        
        # Filtro de Função
        lista_funcoes = ['Todas'] + sorted(df_gastos['Funcao'].unique())
        funcao_selecionada = st.sidebar.selectbox("Selecione uma Função:", lista_funcoes)
        
        # Filtro de Órgão (dependente da Função)
        if funcao_selecionada == 'Todas':
            df_gastos_filtrado = df_gastos
        else:
            df_gastos_filtrado = df_gastos[df_gastos['Funcao'] == funcao_selecionada]
            
        lista_orgaos = ['Todos'] + sorted(df_gastos_filtrado['Orgao_Superior'].unique())
        orgao_selecionado = st.sidebar.selectbox("Selecione um Órgão Superior:", lista_orgaos)

        # Aplicando o filtro de Órgão
        if orgao_selecionado != 'Todos':
            df_gastos_filtrado = df_gastos_filtrado[df_gastos_filtrado['Orgao_Superior'] == orgao_selecionado]
        
        # --- KPIs (Métricas) ---
        total_realizado = df_gastos_filtrado['Valor_Realizado'].sum()
        num_orgaos = df_gastos_filtrado['Orgao_Superior'].nunique()
        num_unidades = df_gastos_filtrado['Unidade_Orcamentaria'].nunique()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Valor Total Realizado (Filtro)", f"R$ {total_realizado*1e-9:.2f} bi")
        col2.metric("Nº de Órgãos Superiores", num_orgaos)
        col3.metric("Nº de Unidades Orçamentárias", num_unidades)

        # --- Gráfico de Gastos ---
        st.subheader("Top 15 Unidades Orçamentárias (por Valor Realizado)")
        
        # Agrupa por unidade orçamentária para o gráfico
        df_plot_gastos = df_gastos_filtrado.groupby('Unidade_Orcamentaria')['Valor_Realizado'].sum().nlargest(15).sort_values(ascending=True)
        
        if not df_plot_gastos.empty:
            fig_gastos, ax_gastos = plt.subplots(figsize=(10, 8))
            bars = ax_gastos.barh(df_plot_gastos.index, df_plot_gastos.values, color='#0072B2')
            
            ax_gastos.set_xlabel('Valor Realizado (em Bilhões de R$)')
            ax_gastos.xaxis.set_major_formatter(ticker.FuncFormatter(formatar_bilhoes))
            ax_gastos.grid(axis='x', linestyle='--', alpha=0.7)
            
            st.pyplot(fig_gastos)
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            
        with st.expander("Ver dados brutos (filtrados)"):
            st.dataframe(df_gastos_filtrado)

    # --- ABA 2: ANÁLISE DA DÍVIDA (AMPLITUDE) ---
    with tab2:
        st.header("Análise de Amplitude: Dívida Pública (Histórico)")
        st.markdown("Use os filtros para explorar o histórico da Dívida Pública Federal.")
        
        # --- Filtros para Dívida ---
        st.sidebar.header("Filtros da Dívida (Histórico)")
        
        # Filtro de Ano (Slider)
        anos_disponiveis = sorted(df_divida['Ano'].unique())
        ano_selecionado = st.sidebar.slider(
            "Selecione o Ano (ou intervalo de anos):",
            min_value=int(min(anos_disponiveis)),
            max_value=int(max(anos_disponiveis)),
            value=(int(min(anos_disponiveis)), int(max(anos_disponiveis))) # Padrão: todos
        )
        
        # Filtro de Tipo de Dívida
        tipos_divida = ['Todos'] + sorted(df_divida['Tipo_Divida'].unique())
        tipo_selecionado = st.sidebar.selectbox("Selecione o Tipo de Dívida:", tipos_divida)

        # Aplicando filtros
        df_divida_filtrado = df_divida[
            (df_divida['Ano'] >= ano_selecionado[0]) &
            (df_divida['Ano'] <= ano_selecionado[1])
        ]
        
        if tipo_selecionado != 'Todos':
            df_divida_filtrado = df_divida_filtrado[df_divida_filtrado['Tipo_Divida'] == tipo_selecionado]
            
        # --- KPIs (Métricas) ---
        valor_max = df_divida_filtrado['Valor_Estoque'].sum()
        data_recente = df_divida_filtrado['Data'].max()
        
        st.metric(f"Valor Total do Estoque (em {data_recente.strftime('%m/%Y')})", f"R$ {valor_max*1e-12:.2f} T")
        
        # --- Gráfico de Evolução ---
        st.subheader("Evolução do Estoque da Dívida (no filtro)")
        
        if not df_divida_filtrado.empty:
            # Agrupa por mês para o gráfico de linha
            df_plot_divida = df_divida_filtrado.groupby('Data')['Valor_Estoque'].sum()
            
            fig_divida, ax_divida = plt.subplots(figsize=(12, 6))
            ax_divida.plot(df_plot_divida.index, df_plot_divida.values, color='#D55E00')
            
            ax_divida.set_ylabel('Valor (em Trilhões de R$)')
            ax_divida.yaxis.set_major_formatter(ticker.FuncFormatter(formatar_trilhoes))
            ax_divida.grid(True, linestyle='--', alpha=0.7)
            
            st.pyplot(fig_divida)
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            
        with st.expander("Ver dados brutos (filtrados)"):
            st.dataframe(df_divida_filtrado)
