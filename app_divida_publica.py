# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v5.7) - Refinamento Visual e de Dados
Melhoria na visualização do gráfico de gastos e correções na interatividade.
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
def carregar_dados_gastos():
    arquivo = "gastos_orcamento_2025.csv"
    try:
        return _processar_gastos(arquivo, 'utf-8')
    except (UnicodeDecodeError, pd.errors.ParserError):
        try:
            return _processar_gastos(arquivo, 'latin1')
        except Exception as e:
            st.error(f"Erro crítico ao ler {arquivo}: {e}")
            return pd.DataFrame()
    except FileNotFoundError:
        st.error(f"ARQUIVO NÃO ENCONTRADO: '{arquivo}'. Verifique se o nome no GitHub está IDÊNTICO.")
        return pd.DataFrame()

def _processar_gastos(arquivo, encoding_type):
    df = pd.read_csv(arquivo, sep=';', encoding=encoding_type)
    
    df = df.rename(columns={
        'NOME FUNÇÃO': 'Funcao',
        'NOME ÓRGÃO SUPERIOR': 'Orgao_Superior',
        'NOME ÓRGÃO SUBORDINADO': 'Orgao_Subordinado',
        'NOME UNIDADE ORÇAMENTÁRIA': 'Unidade_Orcamentaria',
        'ORÇAMENTO REALIZADO (R$)': 'Valor_Realizado'
    })
    
    if 'Valor_Realizado' in df.columns:
        df['Valor_Realizado'] = df['Valor_Realizado'].astype(str)
        df['Valor_Realizado'] = df['Valor_Realizado'].str.replace('.', '', regex=False)
        df['Valor_Realizado'] = df['Valor_Realizado'].str.replace(',', '.', regex=False)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
    
    return df.dropna(subset=['Valor_Realizado'])

@st.cache_data(ttl=3600)
def carregar_dados_divida():
    arquivo = "divida_estoque_historico.csv"
    try:
        return _processar_divida(arquivo, 'utf-8')
    except (UnicodeDecodeError, pd.errors.ParserError):
        try:
            return _processar_divida(arquivo, 'latin1')
        except Exception as e:
            st.error(f"Erro crítico ao ler {arquivo}: {e}")
            return pd.DataFrame()
    except FileNotFoundError:
        st.error(f"ARQUIVO NÃO ENCONTRADO: '{arquivo}'. Verifique se o nome no GitHub está IDÊNTICO.")
        return pd.DataFrame()

def _processar_divida(arquivo, encoding_type):
    df = pd.read_csv(arquivo, sep=';', encoding=encoding_type)
    
    df = df.rename(columns={
        'Mes do Estoque': 'Data',
        'Tipo de Divida': 'Tipo_Divida',
        'Valor do Estoque': 'Valor_Estoque'
    })
    
    if 'Data' in df.columns:
        df['Data'] = df['Data'].astype(str).str.strip()

    try:
        df['Data'] = pd.to_datetime(df['Data'], format='%m/%Y')
    except:
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['Data'])

    df['Ano'] = df['Data'].dt.year
    
    if 'Valor_Estoque' in df.columns:
        df['Valor_Estoque'] = df['Valor_Estoque'].astype(str)
        df['Valor_Estoque'] = df['Valor_Estoque'].str.replace('.', '', regex=False)
        df['Valor_Estoque'] = df['Valor_Estoque'].str.replace(',', '.', regex=False)
        df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce')
        
    return df.dropna(subset=['Valor_Estoque'])

# --- 2. CÉREBRO DE ANÁLISE ---

def gerar_insight_avancado(pergunta, df_gastos, df_divida):
    try:
        if "Pareto" in pergunta:
            df_funcoes = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total_gasto = df_funcoes.sum()
            
            if total_gasto == 0: return "Dados de gastos zerados."

            df_acumulado = df_funcoes.cumsum()
            df_perc = (df_acumulado / total_gasto) * 100
            funcoes_80 = df_perc[df_perc <= 80].count() + 1
            total_funcoes = len(df_funcoes)
            
            top_1 = df_funcoes.index[0]
            top_1_perc = (df_funcoes.iloc[0] / total_gasto) * 100

            res = "### 📉 Análise de Concentração (Regra de Pareto)\n\n"
            res += f"- **Resultado:** Apenas **{funcoes_80} funções** (de {total_funcoes}) concentram **80%** do orçamento.\n"
            res += f"- **Maior Foco:** A função **{top_1}** consome **{top_1_perc:.1f}%** do total."
            return res
            
        elif "Sustentabilidade" in pergunta:
            if df_divida.empty or df_gastos.empty: return "Dados insuficientes."
                
            data_max = df_divida['Data'].max()
            divida_total = df_divida[df_divida['Data'] == data_max]['Valor_Estoque'].sum()
            gasto_total_anual = df_gastos['Valor_Realizado'].sum()
            
            if gasto_total_anual > 0:
                razao = divida_total / gasto_total_anual
                res = "### ⚖️ Índice de Sustentabilidade\n\n"
                res += f"- **Estoque da Dívida:** R$ {divida_total*1e-12:.2f} Tri\n"
                res += f"- **Orçamento Anual:** R$ {gasto_total_anual*1e-12:.2f} Tri\n"
                res += f"- **Índice:** A dívida é **{razao:.1f} vezes maior** que todo o orçamento executado no ano."
                return res
            else:
                return "Gasto anual zerado."

        elif "Listagem dos Gastos" in pergunta:
            df_rank = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            res = "### 📋 Ranking de Gastos (2025)\n\n"
            for func, valor in df_rank.items():
                perc = (valor / total) * 100
                if perc > 0.1: # Mostra apenas relevância > 0.1%
                    res += f"1. **{func}**: R$ {valor*1e-9:.1f} bi ({perc:.1f}%)\n"
            return res
            
        elif "Listagem dos Credores" in pergunta:
            if df_divida.empty: return "Sem dados de dívida."
            data_max = df_divida['Data'].max()
            df_recente = df_divida[df_divida['Data'] == data_max]
            
            if 'Detentor' in df_recente.columns:
                df_rank = df_recente.groupby('Detentor')['Valor_Estoque'].sum().sort_values(ascending=False)
                total = df_rank.sum()
                res = f"### 🏦 Credores da Dívida ({data_max.strftime('%m/%Y')})\n\n"
                for credor, valor in df_rank.items():
                    perc = (valor / total) * 100
                    res += f"1. **{credor}**: R$ {valor*1e-9:.0f} bi ({perc:.1f}%)\n"
                return res
            else:
                df_rank = df_recente.groupby('Tipo_Divida')['Valor_Estoque'].sum().sort_values(ascending=False)
                res = f"### 🏦 Composição da Dívida ({data_max.strftime('%m/%Y')})\n\n"
                res += "**Nota:** Dados detalhados por credor não encontrados no CSV histórico. Exibindo por Tipo.\n"
                for tipo, valor in df_rank.items():
                     res += f"- **{tipo}**: R$ {valor*1e-9:.0f} bi\n"
                return res

        return "Selecione uma análise."
    except Exception as e:
        return f"Erro no cálculo: {e}"

# --- 3. INTERFACE GRÁFICA ---

def format_bi(x, pos): return f'R$ {x*1e-9:.0f} bi'
def format_tri(x, pos): return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Ferramenta de fiscalização baseada em dados oficiais do Tesouro Transparente.")

with st.spinner("Carregando bases de dados..."):
    df_gastos = carregar_dados_gastos()
    df_divida = carregar_dados_divida()

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3 = st.tabs(["📊 Gastos (2025)", "📈 Dívida (Histórico)", "🧠 Análises Avançadas"])
    
    with tab1:
        st.header("Raio-X dos Gastos Públicos")
        col1, col2 = st.columns(2)
        
        # Filtro de Função
        if 'Funcao' in df_gastos.columns:
            funcoes = sorted(list(df_gastos['Funcao'].unique()))
            sel_funcao = col1.selectbox("Filtrar Função:", ['Todas'] + funcoes)
            
            if sel_funcao != 'Todas':
                df_view = df_gastos[df_gastos['Funcao'] == sel_funcao]
                # Se filtrar por função específica, mostra as Unidades (detalhe)
                group_col = 'Unidade_Orcamentaria'
                titulo_grafico = f"Top 10 Unidades em {sel_funcao}"
            else:
                df_view = df_gastos
                # Se ver TUDO, mostra agrupado por FUNÇÃO (visão macro)
                # Isso resolve o problema do gráfico confuso!
                group_col = 'Funcao' 
                titulo_grafico = "Top 10 Funções do Orçamento"
                
            if not df_view.empty:
                top_10 = df_view.groupby(group_col)['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
                
                if not top_10.empty:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.barh(top_10.index, top_10.values, color='#0072B2')
                    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
                    ax.grid(axis='x', linestyle='--', alpha=0.3)
                    ax.set_title(titulo_grafico)
                    st.pyplot(fig)
                else:
                    st.warning("Dados insuficientes para gráfico.")
            else:
                st.warning("Nenhum dado encontrado.")
            
            with st.expander("Ver Tabela Detalhada"):
                st.dataframe(df_view)
        else:
            st.error("Erro: Coluna 'Funcao' não encontrada.")

    with tab2:
        st.header("Trajetória da Dívida Pública")
        df_divida = df_divida.sort_values(by='Data')
        df_linha = df_divida.groupby('Data')['Valor_Estoque'].sum()
        
        if not df_linha.empty:
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            ax2.plot(df_linha.index, df_linha.values, color='#D55E00', linewidth=2)
            ax2.yaxis.set_major_formatter(ticker.FuncFormatter(format_tri))
            ax2.set_title("Evolução do Estoque Total")
            ax2.grid(True, linestyle='--', alpha=0.3)
            st.pyplot(fig2)
            
            ultima = df_linha.iloc[-1]
            st.metric("Estoque Atual", f"R$ {ultima*1e-12:.2f} Trilhões")
        else:
            st.warning("Sem dados para evolução.")

    with tab3:
        st.header("Inteligência de Dados")
        opcoes = ["Selecione...", "📉 Análise de Concentração (Regra de Pareto)", "⚖️ Índice de Sustentabilidade (Dívida vs. Orçamento)", "📋 Listagem dos Gastos (Maior para Menor + %)", "🏦 Listagem dos Credores (Maior para Menor + %)"]
        escolha = st.selectbox("Execute um modelo de análise:", opcoes)
        if escolha != "Selecione...":
            st.markdown("---")
            st.markdown(gerar_insight_avancado(escolha, df_gastos, df_divida))

else:
    st.error("Erro crítico: Arquivos CSV não carregados. Verifique o GitHub.")

