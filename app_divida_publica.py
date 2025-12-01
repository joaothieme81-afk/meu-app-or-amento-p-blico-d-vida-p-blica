# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v9.0 - Final com Treemap)
- Implementa Gráfico Treemap (Hierárquico).
- Separa 'Encargos Especiais' em 'Amortização' e 'Juros'.
- Remove Pareto e ajusta análises.
"""

import streamlit as st
import pandas as pd
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
    
    # Mapeamento (Agora incluindo Grupo de Despesa para separar Juros/Amortização)
    col_map = {
        'funcao': next((c for c in df.columns if 'funcao' in c and 'sub' not in c), None),
        'grupo': next((c for c in df.columns if 'grupo' in c), None), # Nova coluna crucial
        'orgao': next((c for c in df.columns if 'superior' in c), None),
        'valor': next((c for c in df.columns if 'realizado' in c or 'pago' in c), None)
    }
    
    # Renomeia
    df = df.rename(columns={
        col_map['funcao']: 'Funcao',
        col_map['grupo']: 'Grupo_Despesa',
        col_map['orgao']: 'Orgao',
        col_map['valor']: 'Valor'
    })
    
    # Limpeza numérica
    if 'Valor' in df.columns:
        df['Valor'] = df['Valor'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        
        # --- LÓGICA DE CATEGORIZAÇÃO PARA O TREEMAP ---
        # Cria uma nova coluna "Categoria" para separar a Dívida do resto
        def classificar_gasto(row):
            funcao = str(row['Funcao']).lower()
            grupo = str(row['Grupo_Despesa']).lower()
            
            if 'encargos' in funcao or 'dívida' in funcao or 'divida' in funcao:
                # Separa o que é rolagem do que é juros
                if 'amortização' in grupo or 'refinanciamento' in grupo or 'inversões' in grupo:
                    return "Dívida: Amortização/Rolagem"
                else:
                    return "Dívida: Juros e Encargos"
            return "Despesas Sociais e Administrativas"

        df['Categoria_Macro'] = df.apply(classificar_gasto, axis=1)
        
        return df.dropna(subset=['Valor'])
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
    
    df = df.rename(columns={
        col_map['data']: 'Data', 
        col_map['valor']: 'Valor_Estoque',
        col_map['tipo']: 'Tipo_Divida'
    })
    
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

# --- 2. ANÁLISE ESTATÍSTICA ---

def gerar_insight_avancado(pergunta, df_gastos, df_divida):
    try:
        if "Previsão de Pagamento" in pergunta:
            data_max = df_divida['Data'].max()
            divida_total = df_divida[df_divida['Data'] == data_max]['Valor_Estoque'].sum()
            
            # Filtra apenas o que é "Juros e Encargos" ou "Amortização" para calcular o esforço fiscal
            # Aqui consideramos o total gasto com a função Encargos
            gasto_divida_anual = df_gastos[df_gastos['Categoria_Macro'].str.contains("Dívida")]['Valor'].sum()
            
            if gasto_divida_anual > 0:
                anos = divida_total / gasto_divida_anual
                return f"""
### ⏳ Estimativa de Quitação
Esta análise projeta o tempo necessário para zerar o estoque da dívida, assumindo que todo o valor hoje gasto com "Encargos Especiais" (Juros + Amortização) fosse usado efetivamente para abater o principal, e que a dívida parasse de crescer.

- **Estoque Ampliado da Dívida:** R$ {divida_total*1e-12:.2f} Trilhões
- **Fluxo Anual de Pagamento (Orçamento):** R$ {gasto_divida_anual*1e-12:.2f} Trilhões/ano

**Resultado:** Levaria **{anos:.1f} anos** para liquidar o estoque atual.
"""
            else:
                return "Dados de gastos com dívida não encontrados."

        elif "Listagem dos Gastos" in pergunta:
            # Ranking agrupado por Função (excluindo a divisão interna da dívida para simplificar a lista)
            df_rank = df_gastos.groupby('Funcao')['Valor'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            res = "### 📋 Ranking de Gastos (Maior para Menor)\n"
            for f, v in df_rank.items():
                p = (v/total)*100
                if p > 0.5: res += f"1. **{f}**: R$ {v*1e-9:.1f} bi ({p:.1f}%)\n"
            return res

        return "Selecione..."
    except Exception as e: return f"Erro: {e}"

# --- 3. INTERFACE GRÁFICA ---

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Análise hierárquica dos gastos e evolução da dívida (Dados Oficiais do Tesouro).")

with st.spinner("Processando dados..."):
    df_gastos = carregar_dados_gastos()
    df_divida = carregar_dados_divida()

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3 = st.tabs(["📊 Mapa de Gastos (Treemap)", "📈 Dívida (Histórico)", "🧠 Análises"])
    
    with tab1:
        st.header("Distribuição do Orçamento 2025")
        st.info("""
        🟦 **Área Azul:** Despesas com serviços à sociedade (Saúde, Educação, etc).
        🟥/🟧 **Área Quente:** Despesas Financeiras (Dívida).
        Note a distinção entre **Amortização** (Rolagem/Refinanciamento) e **Juros** (Custo efetivo).
        """)
        
        # PREPARAÇÃO PARA O TREEMAP
        # Agrupa por Categoria Macro -> Função para criar a hierarquia
        df_treemap = df_gastos.groupby(['Categoria_Macro', 'Funcao'])['Valor'].sum().reset_index()
        
        # Criação do Treemap
        fig = px.treemap(
            df_treemap, 
            path=['Categoria_Macro', 'Funcao'], 
            values='Valor',
            color='Categoria_Macro',
            color_discrete_map={
                'Despesas Sociais e Administrativas': '#2E86C1', # Azul
                'Dívida: Amortização/Rolagem': '#E74C3C',       # Vermelho
                'Dívida: Juros e Encargos': '#F39C12'           # Laranja
            },
            title="Hierarquia dos Gastos Públicos"
        )
        # Ajusta o layout para mostrar o valor em Bilhões no mouseover
        fig.update_traces(textinfo="label+percent entry", hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}')
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Ver dados em Tabela"):
            st.dataframe(df_treemap.sort_values(by='Valor', ascending=False))

    with tab2:
        st.header("Evolução da Dívida Pública")
        st.warning("⚠️ **Nota:** Valores referentes ao conceito de **Dívida Bruta/Ampliada** (~R$ 11 Tri), abrangendo operações compromissadas e títulos em carteira do BC, diferindo da DPF de mercado (~R$ 7 Tri).")
        
        if 'Data' in df_divida.columns:
            df_divida = df_divida.sort_values(by='Data')
            
            # Filtra para somar componentes (Interna + Externa)
            if 'Tipo_Divida' in df_divida.columns:
                 df_divida_clean = df_divida[~df_divida['Tipo_Divida'].astype(str).str.contains("Total", case=False, na=False)]
            else:
                 df_divida_clean = df_divida

            # Agrupa por data
            df_linha = df_divida_clean.groupby('Data')['Valor_Estoque'].sum()
            
            # Gráfico de área para mostrar volume
            fig2 = px.area(
                x=df_linha.index, 
                y=df_linha.values,
                labels={'x': 'Ano', 'y': 'Estoque (R$)'},
                title="Crescimento do Estoque Total (Ampliado)"
            )
            fig2.update_layout(yaxis_tickformat=".2s") # Formatação simplificada
            
            st.plotly_chart(fig2, use_container_width=True)
            
            ult = df_linha.iloc[-1]
            st.metric("Estoque Atual (Ampliado)", f"R$ {ult*1e-12:.2f} Trilhões")

    with tab3:
        st.header("Inteligência")
        op = st.selectbox("Análise:", [
            "Selecione...", 
            "⏳ Previsão de Pagamento (Cenário Estável)", 
            "📋 Listagem dos Gastos (Ranking)"
        ])
        if op != "Selecione...":
            st.markdown("---")
            st.markdown(gerar_insight_avancado(op, df_gastos, df_divida))

else:
    st.error("Erro crítico: Verifique arquivos CSV no GitHub.")
