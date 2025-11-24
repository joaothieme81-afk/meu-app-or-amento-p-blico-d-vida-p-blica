# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit 
Foca em restaurar o gráfico de gastos e diagnosticar as colunas da dívida.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

st.set_page_config(page_title="Análise Orçamentária", page_icon="🇧🇷", layout="wide")

# --- 1. CARREGAMENTO SIMPLES (O que funcionou antes) ---

@st.cache_data
def carregar_gastos():
    # Tenta ler direto em utf-8 (já que você salvou otimizado)
    try:
        df = pd.read_csv("gastos_orcamento_2025.csv", sep=';', encoding='utf-8')
    except:
        df = pd.read_csv("gastos_orcamento_2025.csv", sep=';', encoding='latin1')
        
    # Limpeza básica (igual a que funcionou no v5.6)
    cols_map = {
        'NOME FUNÇÃO': 'Funcao',
        'NOME ÓRGÃO SUPERIOR': 'Orgao_Superior',
        'NOME UNIDADE ORÇAMENTÁRIA': 'Unidade_Orcamentaria',
        'ORÇAMENTO REALIZADO (R$)': 'Valor_Realizado'
    }
    # Renomeia apenas as que encontrar
    df = df.rename(columns=cols_map)
    
    # Limpeza numérica
    if 'Valor_Realizado' in df.columns:
        df['Valor_Realizado'] = df['Valor_Realizado'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        
    return df

@st.cache_data
def carregar_divida():
    # Tenta ler direto
    try:
        df = pd.read_csv("divida_estoque_historico.csv", sep=';', encoding='utf-8')
    except:
        df = pd.read_csv("divida_estoque_historico.csv", sep=';', encoding='latin1')
    
    return df # Retorna bruto primeiro para analisarmos as colunas

# --- 2. CÉREBRO DE ANÁLISE (Simplificado) ---
def gerar_insight(pergunta, df_gastos, df_divida, col_valor_divida):
    try:
        if "Pareto" in pergunta:
            df_f = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_f.sum()
            df_acc = df_f.cumsum()
            df_perc = (df_acc / total) * 100
            n_80 = df_perc[df_perc <= 80].count() + 1
            return f"### 📉 Pareto\n**{n_80} funções** concentram 80% dos gastos. A maior é **{df_f.index[0]}**."
            
        elif "Sustentabilidade" in pergunta:
            if col_valor_divida not in df_divida.columns: return "Erro: Coluna de valor da dívida não identificada."
            divida = df_divida[col_valor_divida].sum() # Simplificação (soma tudo só para ter um número)
            # O ideal seria pegar o último mês, mas vamos garantir que rode primeiro
            gasto = df_gastos['Valor_Realizado'].sum()
            razao = divida / gasto
            return f"### ⚖️ Sustentabilidade\nA dívida total listada é **{razao:.1f}x** maior que o orçamento realizado."
            
        return "Selecione uma análise."
    except Exception as e: return f"Erro: {e}"

# --- 3. INTERFACE ---

st.title("Análise Orçamentária 🇧🇷")

with st.spinner("Lendo arquivos..."):
    df_gastos = carregar_gastos()
    df_divida_bruto = carregar_divida()

# Verifica Gastos
if not df_gastos.empty and 'Valor_Realizado' in df_gastos.columns:
    
    tab1, tab2, tab3 = st.tabs(["Gastos", "Dívida (Diagnóstico)", "Análises"])
    
    with tab1:
        st.header("Gastos 2025")
        st.info("Estes dados foram carregados com sucesso.")
        
        funcoes = sorted(list(df_gastos['Funcao'].unique())) if 'Funcao' in df_gastos.columns else []
        sel = st.selectbox("Filtrar:", ['Todas'] + funcoes)
        
        df_view = df_gastos if sel == 'Todas' else df_gastos[df_gastos['Funcao'] == sel]
        
        # Gráfico
        top = df_view.groupby('Unidade_Orcamentaria')['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
        fig, ax = plt.subplots(figsize=(10,6))
        ax.barh(top.index, top.values, color='#0072B2')
        st.pyplot(fig)

    with tab2:
        st.header("Dívida Pública")
        
        # --- DIAGNÓSTICO AO VIVO ---
        st.write("### Colunas encontradas no arquivo da Dívida:")
        st.write(list(df_divida_bruto.columns))
        
        # Tentativa de identificar colunas automaticamente
        col_data = next((c for c in df_divida_bruto.columns if 'mes' in c.lower() or 'data' in c.lower()), None)
        col_valor = next((c for c in df_divida_bruto.columns if 'valor' in c.lower() and 'estoque' in c.lower()), None)
        
        if col_data and col_valor:
            st.success(f"Colunas identificadas: Data='{col_data}', Valor='{col_valor}'")
            
            # Limpeza da Dívida (Feita aqui para garantir)
            df_divida = df_divida_bruto.copy()
            df_divida[col_valor] = df_divida[col_valor].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_divida[col_valor] = pd.to_numeric(df_divida[col_valor], errors='coerce')
            
            # Gráfico
            try:
                df_divida[col_data] = pd.to_datetime(df_divida[col_data], format='%m/%Y', errors='coerce')
                df_plot = df_divida.groupby(col_data)[col_valor].sum()
                st.line_chart(df_plot)
                
                # Métrica
                ult = df_plot.iloc[-1]
                st.metric("Estoque Recente", f"R$ {ult*1e-12:.2f} T")
            except:
                st.warning("Não foi possível converter a coluna de data para gráfico temporal.")
                st.dataframe(df_divida.head())
                
        else:
            st.error("Não consegui identificar automaticamente as colunas de Data e Valor. Veja a lista acima.")
            st.dataframe(df_divida_bruto.head())

    with tab3:
        st.header("Insights")
        op = st.selectbox("Análise:", ["Selecione...", "📉 Pareto", "⚖️ Sustentabilidade"])
        if op != "Selecione...":
            col_valor_div = next((c for c in df_divida_bruto.columns if 'valor' in c.lower()), None)
            st.markdown(gerar_insight(op, df_gastos, df_divida_bruto, col_valor_div))

else:
    st.error("Erro: Não foi possível ler o arquivo de Gastos corretamente.")

