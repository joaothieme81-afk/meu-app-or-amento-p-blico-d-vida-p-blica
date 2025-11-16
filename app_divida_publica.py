# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v2.1) para análise da Dívida Pública e Gastos Públicos Federais.

O app se conecta diretamente aos datasets CSV do Tesouro Transparente,
utiliza cache (@st.cache_data) para performance e estabilidade,
e apresenta filtros dinâmicos para a análise dos dados.

[v2.1 - CORREÇÃO]: Atualiza os endpoints (URLs) dos CSVs que mudaram no portal.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Análise Orçamentária do Brasil (v2.1)",
    page_icon="🇧🇷",
    layout="wide"
)

# --- FONTES DE DADOS (ENDPOINTS) ---
# Links diretos para os datasets de CSV no portal do Tesouro (URLs v2.1 ATUALIZADAS)
URL_GASTOS_FUNCAO = "https://www.tesourotransparente.gov.br/ckan/dataset/cofog-despesas-por-funcao-do-governo-central/resource/82a8d1f2-17f1-4861-8d4e-b21a8d0b0b8c/download/cofog-despesas-por-funcao-do-governo-central.csv"
URL_DIVIDA_ESTOQUE = "https://www.tesourotransparente.gov.br/ckan/dataset/estoque-da-divida-publica-federal/resource/30a858f7-66a9-4a4a-867c-d47f96d0b307/download/estoque-da-divida-publica-federal.csv"
URL_DIVIDA_DETENTORES = "https://www.tesourotransparente.gov.br/ckan/dataset/detentores-da-divida-publica-mobiliaria-federal-interna/resource/1359c104-a60d-45f8-8f81-28b3c1d4dc5a/download/detentores-da-divida-publica-mobiliaria-federal-interna.csv"

# --- FUNÇÕES DE CARREGAMENTO E CACHE ---
# @st.cache_data(ttl=86400) armazena os dados baixados por 24h 
# para garantir a performance e estabilidade do app.

@st.cache_data(ttl=86400)
def carregar_dados_gastos():
    """Baixa e limpa os dados de despesas por função (COFOG)."""
    try:
        # CSVs do governo usam ';', encoding 'latin1' e ',' como decimal
        df = pd.read_csv(
            URL_GASTOS_FUNCAO, 
            sep=';', 
            encoding='latin1', 
            decimal=','
        )
        # Limpeza e Renomeação
        df = df.rename(columns={
            'Exercício': 'Ano',
            'Função': 'Funcao',
            'Valor Pago (R$)': 'Valor_Pago'
        })
        # Manter apenas colunas relevantes
        df = df[['Ano', 'Funcao', 'Valor_Pago']]
        # Agrupar dados
        df_agrupado = df.groupby(['Ano', 'Funcao'])['Valor_Pago'].sum().reset_index()
        return df_agrupado
    except Exception as e:
        st.error(f"Erro ao carregar dados de gastos: {e}")
        return pd.DataFrame(columns=['Ano', 'Funcao', 'Valor_Pago'])

@st.cache_data(ttl=86400)
def carregar_dados_divida():
    """Baixa e limpa os dados da Dívida Pública (Estoque e Detentores)."""
    try:
        # Carrega Estoque
        df_estoque = pd.read_csv(
            URL_DIVIDA_ESTOQUE, 
            sep=';', 
            encoding='latin1', 
            decimal=','
        )
        # Limpeza
        df_estoque = df_estoque.rename(columns={'Tipo': 'Tipo_Titulo', 'Valor': 'Valor_Estoque'})
        df_estoque['Data'] = pd.to_datetime(df_estoque['Data'], format='%d/%m/%Y')
        df_estoque = df_estoque[['Data', 'Tipo_Titulo', 'Valor_Estoque']]

        # Carrega Detentores
        df_detentores = pd.read_csv(
            URL_DIVIDA_DETENTORES,
            sep=';', 
            encoding='latin1', 
            decimal=','
        )
        # Limpeza
        df_detentores = df_detentores.rename(columns={'Detentor': 'Detentor', 'Valor': 'Valor_Detido'})
        df_detentores['Data'] = pd.to_datetime(df_detentores['Data'], format='%d/%m/%Y')
        df_detentores = df_detentores[['Data', 'Detentor', 'Valor_Detido']]
        
        return df_estoque, df_detentores
    except Exception as e:
        st.error(f"Erro ao carregar dados da dívida: {e}")
        return pd.DataFrame(columns=['Data', 'Tipo_Titulo', 'Valor_Estoque']), pd.DataFrame(columns=['Data', 'Detentor', 'Valor_Detido'])

# --- FUNÇÕES DE VISUALIZAÇÃO (GRÁFICOS) ---
def formatar_bilhoes(x, pos):
    """Formata o eixo Y para 'R$ 100 bi'."""
    return f'R$ {x*1e-9:.0f} bi'

def criar_grafico_gastos(df_filtrado):
    """Cria um gráfico de barras horizontal com os gastos filtrados."""
    df_plot = df_filtrado.groupby('Funcao')['Valor_Pago'].sum().sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, len(df_plot) * 0.5)) # Altura dinâmica
    bars = ax.barh(df_plot.index, df_plot.values, color='#0072B2')
    
    ax.set_title('Gastos Pagos por Função do Governo', fontsize=16)
    ax.set_xlabel('Valor Pago (em Bilhões de R$)', fontsize=12)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(formatar_bilhoes))
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Adiciona rótulos de dados
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
    """Cria um gráfico de linha da evolução da dívida."""
    # Agrupa por mês para o gráfico de linha
    df_plot = df_filtrado.set_index('Data').resample('M')['Valor_Estoque'].sum()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df_plot.index, df_plot.values, marker='o', linestyle='-', markersize=4, color='#D55E00')
    
    ax.set_title('Evolução do Estoque da Dívida Pública Federal', fontsize=16)
    ax.set_ylabel('Valor (em Trilhões de R$)', fontsize=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'R$ {x*1e-12:.2f} T'))
    ax.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    return fig

def criar_grafico_detentores(df_filtrado):
    """Cria um gráfico de pizza dos detentores da dívida."""
    # Pega a data mais recente dos dados filtrados
    data_recente = df_filtrado['Data'].max()
    df_plot = df_filtrado[df_filtrado['Data'] == data_recente]
    df_plot = df_plot.groupby('Detentor')['Valor_Detido'].sum().sort_values(ascending=False)
    
    # Agrupa detentores menores em "Outros"
    if len(df_plot) > 6:
        outros = df_plot[6:].sum()
        df_plot = df_plot[:6]
        df_plot['Outros'] = outros
        
    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(
        df_plot.values, 
        autopct='%1.1f%%', 
        startangle=90,
        pctdistance=0.85,
        colors=plt.cm.Paired.colors
    )
    
    # Círculo no centro para "donut chart"
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig.gca().add_artist(centre_circle)
    
    ax.set_title(f'Detentores da Dívida (em {data_recente.strftime("%m/%Y")})', fontsize=16)
    
    # Legenda
    legend_labels = [f'{i} - {v/df_plot.sum()*100:.1f}%' for i, v in df_plot.items()]
    ax.legend(
        legend_labels,
        title="Credores",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=10
    )
    
    plt.setp(autotexts, size=10, weight="bold", color="black")
    ax.axis('equal')
    return fig

# --- INTERFACE PRINCIPAL DO APLICATIVO ---

st.title("Análise da Dívida e Gastos Públicos no Brasil (v2.1)")
st.markdown("""
Este aplicativo se conecta aos Dados Abertos do **Tesouro Transparente**
para analisar o Orçamento Federal e a Dívida Pública.
(Os dados são cacheados por 24h para performance).
""")

# --- CARREGAMENTO DOS DADOS ---
# Exibe um spinner enquanto baixa os dados (apenas na primeira carga do dia)
with st.spinner('Carregando dados ao vivo do Tesouro Transparente...'):
    df_gastos = carregar_dados_gastos()
    df_divida_estoque, df_divida_detentores = carregar_dados_divida()

if not df_gastos.empty and not df_divida_estoque.empty:
    
    # --- BARRA LATERAL (FILTROS DINÂMICOS) ---
    st.sidebar.header("Filtros Dinâmicos")
    
    # Filtro de Ano (baseado nos dados de gastos)
    anos_disponiveis = sorted(df_gastos['Ano'].unique(), reverse=True)
    ano_selecionado = st.sidebar.slider(
        "Selecione o Ano (ou intervalo de anos):",
        min_value=int(min(anos_disponiveis)),
        max_value=int(max(anos_disponiveis)),
        value=(int(max(anos_disponiveis))-1, int(max(anos_disponiveis))) # Padrão: últimos 2 anos
    )
    
    # Filtro de Função (baseado nos dados de gastos)
    funcoes_disponiveis = sorted(df_gastos['Funcao'].unique())
    # Define funções padrão para uma visualização inicial limpa
    funcoes_padrao = [f for f in funcoes_disponiveis if 'Encargos' in f or 'Dívida' in f]
    funcoes_padrao.extend(['Previdência Social', 'Saúde', 'Educação'])
    
    funcoes_selecionadas = st.sidebar.multiselect(
        "Selecione as Funções para comparar:",
        options=funcoes_disponiveis,
        default=funcoes_padrao
    )

    # --- APLICANDO FILTROS ---
    
    # Filtro 1: Gastos
    df_gastos_filtrado = df_gastos[
        (df_gastos['Ano'] >= ano_selecionado[0]) &
        (df_gastos['Ano'] <= ano_selecionado[1]) &
        (df_gastos['Funcao'].isin(funcoes_selecionadas))
    ]
    
    # Filtro 2: Dívida (Estoque e Detentores)
    inicio_ano = pd.to_datetime(f"{ano_selecionado[0]}-01-01")
    fim_ano = pd.to_datetime(f"{ano_selecionado[1]}-12-31")
    
    df_divida_estoque_filtrado = df_divida_estoque[
        (df_divida_estoque['Data'] >= inicio_ano) &
        (df_divida_estoque['Data'] <= fim_ano)
    ]
    df_divida_detentores_filtrado = df_divida_detentores[
        (df_divida_detentores['Data'] >= inicio_ano) &
        (df_divida_detentores['Data'] <= fim_ano)
    ]
    
    
    # --- LAYOUT PRINCIPAL (ABAS) ---
    
    tab1, tab2 = st.tabs([
        "📊 Análise de Gastos por Função", 
        "📈 Análise da Dívida Pública"
    ])

    with tab1:
        st.header(f"Gastos por Função ({ano_selecionado[0]} a {ano_selecionado[1]})")
        
        # KPIs (Métricas Principais)
        if not df_gastos_filtrado.empty:
            total_gasto = df_gastos_filtrado['Valor_Pago'].sum()
            st.metric("Total Gasto (no filtro)", f"R$ {total_gasto*1e-9:.2f} Bilhões")
            
            # Gráfico de Barras
            st.subheader(f"Comparativo de Gastos para as Funções selecionadas")
            fig_gastos = criar_grafico_gastos(df_gastos_filtrado)
            st.pyplot(fig_gastos)
            
            with st.expander("Ver dados da tabela de gastos (filtrada)"):
                st.dataframe(df_gastos_filtrado, use_container_width=True)
        else:
            st.warning("Nenhum dado de gasto encontrado para os filtros selecionados.")
            
    with tab2:
        st.header(f"Dívida Pública ({ano_selecionado[0]} a {ano_selecionado[1]})")
        
        # Layout em colunas
        col1, col2 = st.columns([2, 1]) # Gráfico de linha maior
        
        with col1:
            if not df_divida_estoque_filtrado.empty:
                st.subheader("Evolução do Estoque da Dívida")
                fig_evolucao = criar_grafico_evolucao_divida(df_divida_estoque_filtrado)
                st.pyplot(fig_evolucao)
            else:
                st.warning("Nenhum dado de estoque da dívida encontrado para os filtros selecionados.")
        
        with col2:
            if not df_divida_detentores_filtrado.empty:
                st.subheader("Detentores da Dívida (Foto Recente)")
                fig_detentores = criar_grafico_detentores(df_divida_detentores_filtrado)
                st.pyplot(fig_detentores)
            else:
                st.warning("Nenhum dado de detentores da dívida encontrado para os filtros selecionados.")
        
        with st.expander("Ver dados da tabela da Dívida (filtrada)"):
            st.dataframe(df_divida_estoque_filtrado, use_container_width=True)
            st.dataframe(df_divida_detentores_filtrado, use_container_width=True)

else:
    st.error("Falha ao carregar os dados. Verifique os links ou tente novamente mais tarde.")

# --- BARRA LATERAL (SOBRE) ---
st.sidebar.title("Sobre o Aplicativo")
st.sidebar.info(f"""
Este aplicativo é uma ferramenta de análise de dados para o Orçamento Federal e a Dívida Pública do Brasil.

**Arquitetura de Dados:**
1.  Busca dados "ao vivo" dos datasets CSV do Tesouro Transparente.
2.  Usa `@st.cache_data` para garantir alta performance e estabilidade.
3.  Utiliza filtros dinâmicos para uma análise interativa.
""")
