# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v9.2 - Ajuste Final)
- Aba 1: Gráfico de Barras (Ranking).
- Aba 2: Treemap (Hierarquia Encargos com explicação detalhada).
- Aba 3: Evolução Dívida (Área).
- Aba 4: Inteligência (Removida previsão de pagamento).
- Sidebar: Links de Referência Oficiais.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import plotly.express as px
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
        'grupo': next((c for c in df.columns if 'grupo' in c), None),
        'orgao': next((c for c in df.columns if 'superior' in c), None),
        'unidade': next((c for c in df.columns if 'unidade' in c), None),
        'valor': next((c for c in df.columns if 'realizado' in c or 'pago' in c), None)
    }
    
    df = df.rename(columns={
        col_map['funcao']: 'Funcao',
        col_map['grupo']: 'Grupo_Despesa',
        col_map['orgao']: 'Orgao_Superior',
        col_map['unidade']: 'Unidade_Orcamentaria',
        col_map['valor']: 'Valor_Realizado'
    })
    
    if 'Valor_Realizado' in df.columns:
        df['Valor_Realizado'] = df['Valor_Realizado'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        
        # Categorização para o Treemap
        def classificar_divida(row):
            funcao = str(row['Funcao']).lower()
            grupo = str(row['Grupo_Despesa']).lower() if pd.notnull(row['Grupo_Despesa']) else ""
            
            if 'encargos' in funcao or 'dívida' in funcao or 'divida' in funcao:
                if 'amortização' in grupo or 'refinanciamento' in grupo or 'inversões financeiras' in grupo:
                    return "Dívida: Amortização/Rolagem (Principal)"
                else:
                    return "Dívida: Juros e Encargos (Custo)"
            return "Despesas Sociais e Administrativas"

        df['Categoria_Macro'] = df.apply(classificar_divida, axis=1)
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
        
    if 'Tipo_Divida' in df.columns:
        df = df[~df['Tipo_Divida'].astype(str).str.contains("Total", case=False, na=False)]
        
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
A Regra de Pareto (80/20) aplicada aqui demonstra a **rigidez orçamentária**: a grande maioria dos recursos está comprometida com pouquíssimas áreas (principalmente Dívida e Previdência).
"""

        elif "Listagem dos Gastos" in pergunta:
            df_rank = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            res = "### 📋 Ranking de Gastos (Maior para Menor)\n"
            for f, v in df_rank.items():
                p = (v/total)*100
                if p > 0.1: res += f"1. **{f}**: R$ {v*1e-9:.1f} bi ({p:.1f}%)\n"
            return res

        elif "Composição da Dívida" in pergunta:
            data_max = df_divida['Data'].max()
            df_rec = df_divida[df_divida['Data'] == data_max]
            
            col = 'Tipo_Divida' if 'Tipo_Divida' in df_rec.columns else 'Detentor'
            df_rank = df_rec.groupby(col)['Valor_Estoque'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            
            res = f"### 🏦 Composição ({data_max.strftime('%m/%Y')})\n"
            for c, v in df_rank.items():
                p = (v/total)*100
                res += f"- **{c}**: R$ {v*1e-9:.0f} bi ({p:.1f}%)\n"
            return res

        return "Selecione..."
    except Exception as e: return f"Erro: {e}"

# --- 3. INTERFACE GRÁFICA ---

def format_bi(x, pos): return f'R$ {x*1e-9:.0f} bi'
def format_tri(x, pos): return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Ferramenta de fiscalização baseada em dados oficiais.")

with st.spinner("Carregando dados..."):
    df_gastos = carregar_dados_gastos()
    df_divida = carregar_dados_divida()

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Ranking (Barras)", "🗺️ Mapa (Treemap)", "📈 Dívida (Histórico)", "🧠 Análises"])
    
    # ABA 1: BARRAS
    with tab1:
        st.header("Ranking de Gastos por Função")
        col1, col2 = st.columns(2)
        funcoes = sorted(list(df_gastos['Funcao'].unique())) if 'Funcao' in df_gastos.columns else []
        sel = col1.selectbox("Filtrar Função:", ['Todas'] + funcoes)
        
        df_view = df_gastos if sel == 'Todas' else df_gastos[df_gastos['Funcao'] == sel]
        group = 'Funcao' if sel == 'Todas' else 'Unidade_Orcamentaria'
        title = "Top 10 Funções" if sel == 'Todas' else f"Top 10 Unidades em {sel}"
        
        top = df_view.groupby(group)['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(top.index, top.values, color='#0072B2')
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
        ax.grid(axis='x', alpha=0.3)
        ax.set_title(title)
        st.pyplot(fig)
        with st.expander("Ver Tabela"): st.dataframe(df_view)

    # ABA 2: TREEMAP
    with tab2:
        st.header("Mapa Hierárquico de Gastos")
        # EXPLICAÇÃO ATUALIZADA SOBRE ENCARGOS ESPECIAIS
        st.info("""
        **Entenda a divisão dos Encargos Especiais (Área Vermelha/Laranja):**
        
        O orçamento federal agrupa as despesas financeiras na função "Encargos Especiais". Este gráfico revela sua composição interna:
        
        - 🟥 **Amortização/Rolagem (Principal):** É o refinanciamento da dívida. O governo emite novos títulos para pagar os antigos que venceram. Embora movimente trilhões, é uma troca de dívida por dívida (o estoque se mantém).
        - 🟧 **Juros e Encargos (Custo):** É o pagamento efetivo dos juros (o "aluguel" do dinheiro). Este é o custo real para o Estado.
        - 🟦 **Despesas Sociais:** São os gastos finalísticos que retornam em serviços (Saúde, Educação, etc).
        """)
        
        if 'Grupo_Despesa' in df_gastos.columns:
            df_tree = df_gastos.groupby(['Categoria_Macro', 'Funcao'])['Valor_Realizado'].sum().reset_index()
            fig_tree = px.treemap(
                df_tree, path=['Categoria_Macro', 'Funcao'], values='Valor_Realizado',
                color='Categoria_Macro',
                color_discrete_map={
                    'Despesas Sociais e Administrativas': '#2E86C1',
                    'Dívida: Amortização/Rolagem (Principal)': '#C0392B',
                    'Dívida: Juros e Encargos (Custo)': '#F39C12'
                }
            )
            fig_tree.update_traces(textinfo="label+percent entry", hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}')
            st.plotly_chart(fig_tree, use_container_width=True)
        else: st.error("Coluna de Grupo não encontrada.")

    # ABA 3: DÍVIDA
    with tab3:
        st.header("Evolução da Dívida Pública")
        st.warning("⚠️ **Nota:** Valores referentes à **Dívida Bruta/Ampliada** (~R$ 11 Tri).")
        if 'Data' in df_divida.columns:
            df_div = df_divida.sort_values(by='Data')
            if 'Tipo_Divida' in df_div.columns:
                 df_div = df_div[~df_div['Tipo_Divida'].astype(str).str.contains("Total", case=False, na=False)]
            
            df_lin = df_div.groupby('Data')['Valor_Estoque'].sum()
            fig_area = px.area(x=df_lin.index, y=df_lin.values, labels={'x':'Ano', 'y':'R$'}, title="Estoque Total (Ampliado)")
            st.plotly_chart(fig_area, use_container_width=True)
            st.metric("Estoque Atual", f"R$ {df_lin.iloc[-1]*1e-12:.2f} Trilhões")

    # ABA 4: INTELIGÊNCIA (REMOVIDA PREVISÃO DE PAGAMENTO)
    with tab4:
        st.header("Inteligência de Dados")
        opcoes = [
            "Selecione...", 
            "📉 Análise de Concentração (Regra de Pareto)", 
            "📋 Listagem dos Gastos (Maior para Menor)", 
            "🏦 Composição da Dívida (Interna vs Externa)"
        ]
        op = st.selectbox("Análise:", opcoes)
        if op != "Selecione...":
            st.markdown("---")
            st.markdown(gerar_insight_avancado(op, df_gastos, df_divida))

    # --- BARRA LATERAL ---
    st.sidebar.title("Referências e Fontes")
    st.sidebar.info("""
    **Dados utilizados neste projeto:**
    
    - [Séries Temporais do Tesouro Nacional — Tesouro Transparente](https://www.tesourotransparente.gov.br/temas/series-temporais)
    - [Estoque da Dívida Pública Federal - Conjuntos de dados - CKAN](https://www.tesourotransparente.gov.br/ckan/dataset/estoque-da-divida-publica-federal)
    
    *Dados processados a partir dos arquivos CSV oficiais.*
    """)

else:
    st.error("Erro: Arquivos CSV não carregados.")



