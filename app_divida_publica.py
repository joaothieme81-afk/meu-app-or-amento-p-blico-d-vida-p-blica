# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v5.3) - Análises Estatísticas Avançadas
Inclui: Pareto, Sustentabilidade da Dívida e Rankings Percentuais.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Configuração da página
st.set_page_config(
    page_title="Análise Orçamentária do Brasil",
    page_icon="🇧🇷",
    layout="wide"
)

# --- 1. CARREGAMENTO E LIMPEZA DE DADOS ---

@st.cache_data(ttl=3600)
def carregar_dados_gastos(caminho_csv):
    try:
        # Lê o CSV definindo o separador ; e encoding utf-8
        df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
        
        # Padroniza nomes das colunas
        df = df.rename(columns={
            'NOME FUNÇÃO': 'Funcao',
            'NOME ÓRGÃO SUPERIOR': 'Orgao_Superior',
            'NOME UNIDADE ORÇAMENTÁRIA': 'Unidade_Orcamentaria',
            'ORÇAMENTO REALIZADO (R$)': 'Valor_Realizado'
        })
        
        # Limpeza numérica robusta
        if 'Valor_Realizado' in df.columns:
            df['Valor_Realizado'] = df['Valor_Realizado'].astype(str)
            df['Valor_Realizado'] = df['Valor_Realizado'].str.replace('.', '', regex=False)
            df['Valor_Realizado'] = df['Valor_Realizado'].str.replace(',', '.', regex=False)
            df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        
        return df.dropna(subset=['Valor_Realizado'])
    except Exception as e:
        st.error(f"Erro ao ler arquivo de gastos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def carregar_dados_divida(caminho_csv):
    try:
        df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
        
        df = df.rename(columns={
            'Mes do Estoque': 'Data',
            'Tipo de Divida': 'Tipo_Divida',
            'Valor do Estoque': 'Valor_Estoque'
        })
        
        try:
            df['Data'] = pd.to_datetime(df['Data'], format='%m/%Y')
        except:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            
        df['Ano'] = df['Data'].dt.year
        
        if 'Valor_Estoque' in df.columns:
            df['Valor_Estoque'] = df['Valor_Estoque'].astype(str)
            df['Valor_Estoque'] = df['Valor_Estoque'].str.replace('.', '', regex=False)
            df['Valor_Estoque'] = df['Valor_Estoque'].str.replace(',', '.', regex=False)
            df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce')
            
        return df.dropna(subset=['Valor_Estoque'])
    except Exception as e:
        st.error(f"Erro ao ler arquivo da dívida: {e}")
        return pd.DataFrame()

# --- 2. MOTOR DE ANÁLISE ESTATÍSTICA ---

def gerar_analise_avancada(tipo, df_gastos, df_divida):
    try:
        # ANÁLISE 1: REGRA DE PARETO (Concentração de Gastos)
        if "Pareto" in tipo:
            df_funcoes = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total_gasto = df_funcoes.sum()
            
            # Cálculo acumulado
            df_acumulado = df_funcoes.cumsum()
            df_perc = (df_acumulado / total_gasto) * 100
            
            # Quantas funções somam 80%?
            funcoes_80 = df_perc[df_perc <= 80].count() + 1 # +1 para incluir a que cruza a linha
            total_funcoes = len(df_funcoes)
            top_1 = df_funcoes.index[0]
            top_1_perc = (df_funcoes.iloc[0] / total_gasto) * 100
            
            res = "### 📉 Análise de Concentração (Regra de Pareto)\n\n"
            res += f"Verifica se poucos setores consomem a maioria dos recursos (Princípio 80/20).\n\n"
            res += f"- **Resultado:** Apenas **{funcoes_80} funções** (de um total de {total_funcoes}) concentram **80%** de todo o orçamento realizado.\n"
            res += f"- **Maior Concentração:** A função **{top_1}** sozinha consome **{top_1_perc:.1f}%** de todo o dinheiro público listado.\n"
            res += f"- **Conclusão:** O orçamento é altamente concentrado e rígido, com pouca margem para outras áreas."
            return res

        # ANÁLISE 2: SUSTENTABILIDADE (Dívida vs Orçamento)
        elif "Sustentabilidade" in tipo:
            data_max = df_divida['Data'].max()
            divida_total = df_divida[df_divida['Data'] == data_max]['Valor_Estoque'].sum()
            gasto_total_anual = df_gastos['Valor_Realizado'].sum()
            
            razao = divida_total / gasto_total_anual
            anos_pagamento = razao
            
            res = "### ⚖️ Índice de Sustentabilidade da Dívida\n\n"
            res += f"Compara o tamanho da dívida com a capacidade anual de execução de despesas do país.\n\n"
            res += f"- **Estoque da Dívida:** R$ {divida_total*1e-12:.2f} Trilhões\n"
            res += f"- **Orçamento Realizado (Ano):** R$ {gasto_total_anual*1e-12:.2f} Trilhões\n"
            res += f"- **Índice:** O estoque da dívida é **{razao:.1f} vezes maior** que todo o orçamento executado no ano.\n\n"
            res += f"**Interpretação:** Em um cenário hipotético e impossível onde o governo parasse de gastar com tudo (saúde, educação, salários) e usasse cada centavo apenas para pagar o principal da dívida, levaria **{anos_pagamento:.1f} anos** para quitá-la."
            return res

        # ANÁLISE 3: LISTAGEM DE GASTOS (Com Porcentagem)
        elif "Listagem dos Gastos" in tipo:
            df_rank = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            
            res = "### 📋 Listagem de Gastos por Função (Do maior para o menor)\n"
            res += "Valores e participação percentual no orçamento total analisado:\n\n"
            
            for func, valor in df_rank.items():
                perc = (valor / total) * 100
                res += f"1. **{func}**: R$ {valor*1e-9:.1f} bi (**{perc:.1f}%**)\n"
            return res

        # ANÁLISE 4: LISTAGEM DE CREDORES (Com Porcentagem)
        elif "Listagem dos Credores" in tipo:
            data_max = df_divida['Data'].max()
            df_recente = df_divida[df_divida['Data'] == data_max]
            df_rank = df_recente.groupby('Detentor')['Valor_Estoque'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            
            res = f"### 🏦 Listagem dos Credores da Dívida ({data_max.strftime('%m/%Y')})\n"
            res += "Quem detém os títulos da dívida pública brasileira:\n\n"
            
            for credor, valor in df_rank.items():
                perc = (valor / total) * 100
                res += f"1. **{credor}**: R$ {valor*1e-9:.0f} bi (**{perc:.1f}%**)\n"
            return res

        return "Selecione uma análise."
    except Exception as e:
        return f"Erro no cálculo: {e}"

# --- 3. INTERFACE GRÁFICA ---

def format_bi(x, pos): return f'R$ {x*1e-9:.0f} bi'
def format_tri(x, pos): return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Ferramenta de fiscalização baseada em dados oficiais do Tesouro Transparente.")

with st.spinner("Carregando bases de dados oficiais..."):
    df_gastos = carregar_dados_gastos("gastos_orcamento_2025.csv")
    df_divida = carregar_dados_divida("divida_estoque_historico.csv")

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3 = st.tabs(["📊 Gastos (2025)", "📈 Dívida (Histórico)", "🧠 Análises Avançadas"])
    
    # ABA 1: GASTOS
    with tab1:
        st.header("Raio-X dos Gastos Públicos")
        col1, col2 = st.columns(2)
        funcoes = sorted(df_gastos['Funcao'].unique())
        sel_funcao = col1.selectbox("Filtrar Função:", ['Todas'] + funcoes)
        
        if sel_funcao != 'Todas':
            df_view = df_gastos[df_gastos['Funcao'] == sel_funcao]
        else:
            df_view = df_gastos
            
        top_10 = df_view.groupby('Unidade_Orcamentaria')['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(top_10.index, top_10.values, color='#0072B2')
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_xlabel("Valor Pago")
        st.pyplot(fig)
        
        with st.expander("Ver Tabela de Dados"):
            st.dataframe(df_view)

    # ABA 2: DÍVIDA
    with tab2:
        st.header("Trajetória da Dívida Pública")
        df_linha = df_divida.groupby('Data')['Valor_Estoque'].sum()
        
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        ax2.plot(df_linha.index, df_linha.values, color='#D55E00', linewidth=2)
        ax2.yaxis.set_major_formatter(ticker.FuncFormatter(format_tri))
        ax2.grid(True, linestyle='--', alpha=0.3)
        st.pyplot(fig2)
        
        ultima = df_linha.iloc[-1]
        st.metric("Estoque Atual", f"R$ {ultima*1e-12:.2f} Trilhões")

    # ABA 3: ANÁLISES AVANÇADAS
    with tab3:
        st.header("Inteligência de Dados")
        st.markdown("Algoritmos estatísticos aplicados aos dados brutos para gerar insights complexos.")
        
        opcoes = [
            "Selecione uma análise...",
            "📉 Análise de Concentração (Regra de Pareto)",
            "⚖️ Índice de Sustentabilidade (Dívida vs. Orçamento)",
            "📋 Listagem dos Gastos (Maior para Menor + %)",
            "🏦 Listagem dos Credores (Maior para Menor + %)"
        ]
        
        escolha = st.selectbox("Execute um modelo de análise:", opcoes)
        
        if escolha != "Selecione uma análise...":
            st.markdown("---")
            res = gerar_analise_avancada(escolha, df_gastos, df_divida)
            st.markdown(res)

else:
    st.error("Erro: Arquivos CSV não encontrados no GitHub.")