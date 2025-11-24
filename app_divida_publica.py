# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v7.3) - Ajuste Fino Final
- Gráfico de Dívida separado por Tipo (Interna vs Externa) para evitar erro de soma.
- Funcionalidades interativas focadas em Pareto e Rankings disponíveis.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import unicodedata

# Configuração da página
st.set_page_config(
    page_title="Análise Orçamentária do Brasil",
    page_icon="🇧🇷",
    layout="wide"
)

# --- FUNÇÕES AUXILIARES ---

def normalizar_colunas(df):
    """Padroniza nomes de colunas."""
    novas = {}
    for col in df.columns:
        nfkd = unicodedata.normalize('NFKD', str(col))
        sem_acento = u"".join([c for c in nfkd if not unicodedata.combining(c)])
        novas[col] = sem_acento.lower().strip().replace(' ', '_')
    return df.rename(columns=novas)

def traduzir_data_pt_br(data_str):
    """Converte datas PT-BR (jan/23) para datetime."""
    if not isinstance(data_str, str): return data_str
    mapa = {'jan':'01','fev':'02','mar':'03','abr':'04','mai':'05','jun':'06',
            'jul':'07','ago':'08','set':'09','out':'10','nov':'11','dez':'12'}
    parte = data_str[:3].lower()
    if parte in mapa:
        return pd.to_datetime(f"{mapa[parte]}{data_str[3:]}", format='%m/%y', errors='coerce')
    return pd.to_datetime(data_str, format='%m/%Y', errors='coerce')

# --- 1. CARREGAMENTO DE DADOS ---

@st.cache_data(ttl=3600)
def carregar_dados_gastos():
    arquivo = "gastos_orcamento_2025.csv"
    try:
        df = pd.read_csv(arquivo, sep=';', encoding='utf-8')
    except:
        try:
            df = pd.read_csv(arquivo, sep=';', encoding='latin1')
        except:
            return pd.DataFrame()

    df = normalizar_colunas(df)
    
    col_map = {
        'funcao': next((c for c in df.columns if 'funcao' in c and 'sub' not in c), None),
        'orgao_superior': next((c for c in df.columns if 'superior' in c), None),
        'unidade_orcamentaria': next((c for c in df.columns if 'unidade' in c), None),
        'valor': next((c for c in df.columns if 'realizado' in c or 'pago' in c), None)
    }
    
    df = df.rename(columns={
        col_map['funcao']: 'Funcao',
        col_map['orgao_superior']: 'Orgao_Superior',
        col_map['unidade_orcamentaria']: 'Unidade_Orcamentaria',
        col_map['valor']: 'Valor_Realizado'
    })
    
    if 'Valor_Realizado' in df.columns:
        df['Valor_Realizado'] = df['Valor_Realizado'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        return df.dropna(subset=['Valor_Realizado'])
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def carregar_dados_divida():
    arquivo = "divida_estoque_historico.csv"
    try:
        df = pd.read_csv(arquivo, sep=';', encoding='utf-8')
    except:
        try:
            df = pd.read_csv(arquivo, sep=';', encoding='latin1')
        except:
            return pd.DataFrame()

    df = normalizar_colunas(df)
    
    col_map = {
        'data': next((c for c in df.columns if 'mes' in c or 'data' in c), None),
        'valor': next((c for c in df.columns if 'valor' in c), None),
        'tipo': next((c for c in df.columns if 'tipo' in c), None)
    }
    
    rename_dict = {col_map['data']: 'Data', col_map['valor']: 'Valor_Estoque'}
    if col_map['tipo']: rename_dict[col_map['tipo']] = 'Tipo_Divida'
    
    df = df.rename(columns=rename_dict)
    
    if 'Data' in df.columns:
        df['Data'] = df['Data'].astype(str).str.strip()
        df['Data'] = df['Data'].apply(traduzir_data_pt_br)
        df = df.dropna(subset=['Data'])
        df['Ano'] = df['Data'].dt.year

    if 'Valor_Estoque' in df.columns:
        df['Valor_Estoque'] = df['Valor_Estoque'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce')
        
    return df.dropna(subset=['Valor_Estoque'])

# --- 2. CÉREBRO DE ANÁLISE ---

def gerar_insight_avancado(pergunta, df_gastos, df_divida):
    try:
        if "Pareto" in pergunta:
            df_f = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_f.sum()
            df_acc = df_f.cumsum()
            df_perc = (df_acc / total) * 100
            n_80 = df_perc[df_perc <= 80].count() + 1
            top_1 = df_f.index[0]
            top_1_perc = (df_f.iloc[0] / total) * 100
            
            return f"""
### 📉 Análise de Concentração (Regra de Pareto)
- **Resultado:** Apenas **{n_80} funções** concentram **80%** de todo o orçamento realizado.
- **Maior Foco:** A função **{top_1}** sozinha representa **{top_1_perc:.1f}%** dos gastos.

---
**💡 Entenda o Conceito:**
A Regra de Pareto (80/20) aplicada aqui demonstra a **rigidez orçamentária**: a grande maioria dos recursos está comprometida com pouquíssimas áreas (principalmente Dívida e Previdência), deixando pouco espaço para investimentos discricionários em outros setores.
"""

        elif "Listagem dos Gastos" in pergunta:
            df_rank = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            res = "### 📋 Ranking de Gastos (Maior para Menor)\n"
            for f, v in df_rank.items():
                p = (v/total)*100
                if p > 0.1: res += f"1. **{f}**: R$ {v*1e-9:.1f} bi ({p:.1f}%)\n"
            return res

        elif "Interna vs Externa" in pergunta:
            data_max = df_divida['Data'].max()
            df_rec = df_divida[df_divida['Data'] == data_max]
            
            if 'Tipo_Divida' in df_rec.columns:
                # Remove "Total" para ver só a composição
                df_tipo = df_rec[~df_rec['Tipo_Divida'].str.contains("Total", case=False, na=False)]
                df_rank = df_tipo.groupby('Tipo_Divida')['Valor_Estoque'].sum().sort_values(ascending=False)
                total = df_rank.sum()
                
                res = f"### 🏦 Composição da Dívida ({data_max.strftime('%m/%Y')})\n"
                for t, v in df_rank.items():
                    p = (v/total)*100
                    res += f"- **{t}**: R$ {v*1e-9:.0f} bi ({p:.1f}%)\n"
                return res
            else:
                return "Coluna 'Tipo de Dívida' não encontrada para essa análise."

        return "Selecione..."
    except Exception as e: return f"Erro: {e}"

# --- 3. INTERFACE ---

def format_bi(x, pos): return f'R$ {x*1e-9:.0f} bi'
def format_tri(x, pos): return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Dados oficiais do Tesouro Transparente.")

with st.spinner("Carregando..."):
    df_gastos = carregar_dados_gastos()
    df_divida = carregar_dados_divida()

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3 = st.tabs(["📊 Gastos", "📈 Dívida", "🧠 Análises"])
    
    with tab1:
        st.header("Raio-X dos Gastos")
        st.info("ℹ️ **Nota:** 'Encargos Especiais' inclui o serviço da dívida (amortização e juros).")
        
        col1, col2 = st.columns(2)
        if 'Funcao' in df_gastos.columns:
            funcoes = sorted(list(df_gastos['Funcao'].unique()))
            sel = col1.selectbox("Filtrar:", ['Todas'] + funcoes)
            
            if sel == 'Todas':
                df_view = df_gastos
                # Visão Macro: Agrupa por FUNÇÃO
                group = 'Funcao'
                title = "Top 10 Funções do Orçamento"
            else:
                df_view = df_gastos[df_gastos['Funcao'] == sel]
                # Visão Micro: Agrupa por UNIDADE
                group = 'Unidade_Orcamentaria'
                title = f"Top 10 Unidades em {sel}"
            
            top = df_view.groupby(group)['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(top.index, top.values, color='#0072B2')
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
            ax.grid(axis='x', alpha=0.3)
            ax.set_title(title)
            st.pyplot(fig)
            
            with st.expander("Dados Detalhados"): st.dataframe(df_view)

    with tab2:
        st.header("Evolução da Dívida Pública")
        
        if 'Data' in df_divida.columns and 'Tipo_Divida' in df_divida.columns:
            df_divida = df_divida.sort_values(by='Data')
            
            # Filtra apenas Interna e Externa para o gráfico (Ignora linhas de Total se houver)
            # Isso evita a duplicação e mostra a composição
            df_clean = df_divida[df_divida['Tipo_Divida'].str.contains("Interna|Externa", case=False, na=False)]
            
            # Pivot para ter colunas separadas para Interna e Externa
            df_pivot = df_clean.pivot_table(index='Data', columns='Tipo_Divida', values='Valor_Estoque', aggfunc='sum')
            
            # Gráfico de Área Empilhada (Mostra a soma visualmente sem duplicar)
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            df_pivot.plot(kind='area', ax=ax2, alpha=0.6)
            
            ax2.yaxis.set_major_formatter(ticker.FuncFormatter(format_tri))
            ax2.set_title("Evolução do Estoque (Interna vs. Externa)")
            ax2.grid(True, alpha=0.3)
            st.pyplot(fig2)
            
            # Métrica (Soma apenas das partes filtradas para garantir precisão)
            ult_data = df_pivot.index[-1]
            total_atual = df_pivot.iloc[-1].sum()
            st.metric(f"Estoque Total Estimado ({ult_data.strftime('%m/%Y')})", f"R$ {total_atual*1e-12:.2f} Trilhões")
            
        else:
            st.error("Colunas 'Data' ou 'Tipo_Divida' não encontradas.")

    with tab3:
        st.header("Inteligência")
        op = st.selectbox("Análise:", ["Selecione...", "📉 Pareto (Concentração)", "📋 Ranking de Gastos", "🏦 Dívida Interna vs Externa"])
        if op != "Selecione...":
            st.markdown(gerar_insight_avancado(op, df_gastos, df_divida))

else:
    st.error("Erro: Arquivos CSV não carregados.")


