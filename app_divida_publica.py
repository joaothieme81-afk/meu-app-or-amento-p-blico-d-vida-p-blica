# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v9.0 - Final com Treemap)
- Aba 1: Gráfico de Barras (Visão Geral).
- Aba 2: Treemap (Detalhamento Hierárquico dos Encargos).
- Aba 3: Evolução da Dívida.
- Aba 4: Análises (Pareto).
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
    
    # Mapeamento expandido para incluir GRUPO DE DESPESA
    col_map = {
        'funcao': next((c for c in df.columns if 'funcao' in c and 'sub' not in c), None),
        'grupo': next((c for c in df.columns if 'grupo' in c), None), # Nova coluna essencial para o Treemap
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
    
    # Limpeza numérica
    if 'Valor_Realizado' in df.columns:
        df['Valor_Realizado'] = df['Valor_Realizado'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
        
        # --- Categorização para o Treemap ---
        def classificar_divida(row):
            funcao = str(row['Funcao']).lower()
            grupo = str(row['Grupo_Despesa']).lower()
            
            if 'encargos' in funcao or 'dívida' in funcao or 'divida' in funcao:
                # Separa Rolagem (Amortização) de Custo (Juros)
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

# --- 2. ANÁLISE ---

def gerar_insight_avancado(pergunta, df_gastos):
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
        return "Selecione..."
    except Exception as e: return f"Erro: {e}"

# --- 3. INTERFACE GRÁFICA ---

def format_bi(x, pos): return f'R$ {x*1e-9:.0f} bi'
def format_tri(x, pos): return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Dados oficiais do Tesouro Transparente e Portal da Transparência.")

with st.spinner("Carregando..."):
    df_gastos = carregar_dados_gastos()
    df_divida = carregar_dados_divida()

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Ranking de Gastos (Barras)", "🗺️ Mapa de Gastos (Treemap)", "📈 Dívida (Histórico)", "🧠 Análises"])
    
    # ABA 1: RANKING DE GASTOS (BARRAS) - Mantida como você queria
    with tab1:
        st.header("Ranking de Gastos por Função")
        st.info("ℹ️ Visão geral dos maiores grupos de despesa.")
        
        col1, col2 = st.columns(2)
        funcoes = sorted(list(df_gastos['Funcao'].unique())) if 'Funcao' in df_gastos.columns else []
        sel = col1.selectbox("Filtrar Função (Barras):", ['Todas'] + funcoes)
        
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
        
        with st.expander("Ver Dados Detalhados"): st.dataframe(df_view)

    # ABA 2: MAPA DE GASTOS (TREEMAP) - Nova Visualização Hierárquica
    with tab2:
        st.header("Mapa Hierárquico de Gastos (Treemap)")
        st.info("""
        Este gráfico permite visualizar a **composição interna** dos grandes grupos.
        Destaque para a separação dentro dos Encargos Especiais:
        - 🟥 **Amortização/Rolagem:** Pagamento do principal da dívida (refinanciamento).
        - 🟧 **Juros:** Custo efetivo da dívida.
        - 🟦 **Despesas Sociais:** Demais áreas do governo.
        """)
        
        # Prepara dados para o Treemap
        # Agrupa por Categoria Macro (Dívida vs Social) -> Função -> Grupo de Despesa (opcional, para detalhe)
        if 'Grupo_Despesa' in df_gastos.columns:
            df_tree = df_gastos.groupby(['Categoria_Macro', 'Funcao'])['Valor_Realizado'].sum().reset_index()
            
            fig_tree = px.treemap(
                df_tree,
                path=['Categoria_Macro', 'Funcao'],
                values='Valor_Realizado',
                color='Categoria_Macro',
                color_discrete_map={
                    'Despesas Sociais e Administrativas': '#2E86C1',
                    'Dívida: Amortização/Rolagem (Principal)': '#C0392B',
                    'Dívida: Juros e Encargos (Custo)': '#F39C12'
                },
                title="Distribuição do Orçamento: Dívida vs. Sociedade"
            )
            # Formatação do tooltip
            fig_tree.update_traces(
                textinfo="label+percent entry",
                hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}'
            )
            
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.error("Coluna 'Grupo de Despesa' não encontrada para gerar o Treemap detalhado.")

    # ABA 3: DÍVIDA (HISTÓRICO) - Mantida
    with tab3:
        st.header("Evolução da Dívida Pública")
        st.warning("⚠️ **Nota Metodológica:** Valores referentes ao conceito de **Dívida Bruta/Ampliada** (~R$ 11 Tri), abrangendo operações compromissadas e títulos em carteira do BC.")
        
        if 'Data' in df_divida.columns:
            df_divida = df_divida.sort_values(by='Data')
            # Filtra Total para somar componentes
            if 'Tipo_Divida' in df_divida.columns:
                 df_divida_clean = df_divida[~df_divida['Tipo_Divida'].astype(str).str.contains("Total", case=False, na=False)]
            else:
                 df_divida_clean = df_divida

            df_linha = df_divida_clean.groupby('Data')['Valor_Estoque'].sum()
            
            # Gráfico de área interativo com Plotly (mais moderno que matplotlib para séries temporais)
            fig_area = px.area(
                x=df_linha.index, 
                y=df_linha.values,
                labels={'x': 'Ano', 'y': 'Estoque (R$)'},
                title="Crescimento do Estoque Total (Ampliado)"
            )
            st.plotly_chart(fig_area, use_container_width=True)
            
            ult = df_linha.iloc[-1]
            st.metric(f"Estoque Atual", f"R$ {ult*1e-12:.2f} Trilhões")
        else:
            st.error("Erro na coluna de Data.")

    # ABA 4: ANÁLISES (PARETO) - Focada
    with tab4:
        st.header("Inteligência")
        op = st.selectbox("Análise:", ["Selecione...", "📉 Análise de Concentração (Regra de Pareto)"])
        if op != "Selecione...":
            st.markdown("---")
            st.markdown(gerar_insight_avancado(op, df_gastos))

else:
    st.error("Erro: Arquivos CSV não carregados.")

