# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v7.0 - Versão Definitiva Completa)
- Leitura robusta de datas em português (jan/23).
- Gráficos de gastos agrupados por Função (mais claros).
- Todas as análises avançadas (Pareto, Sustentabilidade) restauradas.
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

# --- FUNÇÕES AUXILIARES DE TRADUÇÃO E LIMPEZA ---

def traduzir_data_pt_br(data_str):
    """Converte datas como 'jan/23' ou 'nov/22' para datetime."""
    if not isinstance(data_str, str): return data_str
    
    mapa_meses = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    
    # Pega as 3 primeiras letras minúsculas
    parte_mes = data_str[:3].lower()
    if parte_mes in mapa_meses:
        # Assume formato 'mes/ano' (ex: jan/23 -> 01/2023)
        # O ano está após a barra (índice 4 em diante)
        resto = data_str[3:] # ex: /23
        data_formatada = f"{mapa_meses[parte_mes]}{resto}" # 01/23
        return pd.to_datetime(data_formatada, format='%m/%y', errors='coerce')
    
    # Se não for pt-br, tenta padrão
    return pd.to_datetime(data_str, format='%m/%Y', errors='coerce')

# --- 1. CARREGAMENTO DE DADOS ---

@st.cache_data(ttl=3600)
def carregar_dados_gastos():
    arquivo = "gastos_orcamento_2025.csv"
    try:
        # Tenta ler com utf-8 primeiro (seu arquivo otimizado)
        df = pd.read_csv(arquivo, sep=';', encoding='utf-8')
    except:
        try:
            # Fallback para latin1
            df = pd.read_csv(arquivo, sep=';', encoding='latin1')
        except Exception as e:
            st.error(f"Erro ao ler gastos: {e}")
            return pd.DataFrame()

    # Mapeamento direto das colunas (baseado no seu print)
    df = df.rename(columns={
        'NOME FUNÇÃO': 'Funcao',
        'NOME ÓRGÃO SUPERIOR': 'Orgao_Superior',
        'NOME UNIDADE ORÇAMENTÁRIA': 'Unidade_Orcamentaria',
        'ORÇAMENTO REALIZADO (R$)': 'Valor_Realizado'
    })
    
    # Limpeza numérica
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
        df = pd.read_csv(arquivo, sep=';', encoding='utf-8')
    except:
        try:
            df = pd.read_csv(arquivo, sep=';', encoding='latin1')
        except Exception as e:
            st.error(f"Erro ao ler dívida: {e}")
            return pd.DataFrame()

    # Renomeia colunas
    df = df.rename(columns={
        'Mes do Estoque': 'Data_Original',
        'Tipo de Divida': 'Tipo_Divida',
        'Valor do Estoque': 'Valor_Estoque',
        'Detentor': 'Detentor' # Tenta achar detentor se existir
    })
    
    # Tratamento de Data PT-BR (O segredo para o gráfico funcionar)
    if 'Data_Original' in df.columns:
        df['Data_Original'] = df['Data_Original'].astype(str).str.strip()
        df['Data'] = df['Data_Original'].apply(traduzir_data_pt_br)
        df = df.dropna(subset=['Data'])
        df['Ano'] = df['Data'].dt.year
    else:
        st.error("Coluna 'Mes do Estoque' não encontrada.")
        return pd.DataFrame()

    # Limpeza numérica
    if 'Valor_Estoque' in df.columns:
        df['Valor_Estoque'] = df['Valor_Estoque'].astype(str)
        df['Valor_Estoque'] = df['Valor_Estoque'].str.replace('.', '', regex=False)
        df['Valor_Estoque'] = df['Valor_Estoque'].str.replace(',', '.', regex=False)
        df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce')
        
    return df.dropna(subset=['Valor_Estoque'])

# --- 2. CÉREBRO DE ANÁLISE AVANÇADA (PARETO & CIA) ---

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
            res += f"- **Resultado:** Apenas **{funcoes_80} funções** (de um total de {total_funcoes}) consomem **80%** de todo o orçamento realizado.\n"
            res += f"- **Maior Concentração:** A função **{top_1}** sozinha representa **{top_1_perc:.1f}%** dos gastos.\n\n"
            res += "--- \n**💡 O que isso significa?**\n"
            res += "A Regra de Pareto (80/20) aplicada aqui mostra a rigidez orçamentária: a grande maioria dos recursos está 'travada' em pouquíssimas áreas (geralmente Dívida/Encargos e Previdência), sobrando muito pouco para as outras dezenas de funções do Estado."
            return res
            
        elif "Sustentabilidade" in pergunta:
            if df_divida.empty: return "Dados de dívida insuficientes."
            data_max = df_divida['Data'].max()
            divida_total = df_divida[df_divida['Data'] == data_max]['Valor_Estoque'].sum()
            gasto_total_anual = df_gastos['Valor_Realizado'].sum()
            
            if gasto_total_anual > 0:
                razao = divida_total / gasto_total_anual
                anos_estimados = razao 
                res = "### ⚖️ Índice de Sustentabilidade da Dívida\n\n"
                res += f"- **Estoque Total da Dívida:** R$ {divida_total*1e-12:.2f} Trilhões\n"
                res += f"- **Orçamento Total Executado (Ano):** R$ {gasto_total_anual*1e-12:.2f} Trilhões\n\n"
                res += f"**O índice é de {razao:.1f}x.**\n\n"
                res += f"**Interpretação:** A dívida pública equivale a **{razao:.1f} anos inteiros** de execução orçamentária do Brasil. "
                res += f"Ou seja, mesmo que o governo parasse de pagar tudo (saúde, educação, funcionalismo) e usasse 100% do dinheiro para pagar a dívida principal, levaria {anos_estimados:.1f} anos para quitá-la."
                return res
            else:
                return "Gasto anual zerado."

        elif "Listagem dos Gastos" in pergunta:
            # Agrupa por FUNÇÃO para ser mais claro (não Unidade)
            df_rank = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            res = "### 📋 Ranking de Gastos por Função (2025)\n\n"
            for func, valor in df_rank.items():
                perc = (valor / total) * 100
                if perc > 0.1: # Filtra os muito pequenos
                    res += f"1. **{func}**: R$ {valor*1e-9:.1f} bi (**{perc:.1f}%**)\n"
            return res
            
        elif "Listagem dos Credores" in pergunta:
            if df_divida.empty: return "Sem dados."
            data_max = df_divida['Data'].max()
            df_recente = df_divida[df_divida['Data'] == data_max]
            
            # Se tiver coluna Detentor, usa. Se não, usa Tipo_Divida.
            col_agrupamento = 'Detentor' if 'Detentor' in df_recente.columns else 'Tipo_Divida'
            
            df_rank = df_recente.groupby(col_agrupamento)['Valor_Estoque'].sum().sort_values(ascending=False)
            total = df_rank.sum()
            
            label = "Credor" if col_agrupamento == 'Detentor' else "Tipo de Título"
            res = f"### 🏦 Composição da Dívida por {label} ({data_max.strftime('%m/%Y')})\n\n"
            
            for item, valor in df_rank.items():
                perc = (valor / total) * 100
                res += f"1. **{item}**: R$ {valor*1e-9:.0f} bi (**{perc:.1f}%**)\n"
            return res

        return "Selecione uma análise."
    except Exception as e:
        return f"Erro no cálculo: {e}"

# --- 3. INTERFACE GRÁFICA ---

def format_bi(x, pos): return f'R$ {x*1e-9:.0f} bi'
def format_tri(x, pos): return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Ferramenta de fiscalização baseada em dados oficiais do Tesouro Transparente.")

with st.spinner("Carregando e processando bases de dados oficiais..."):
    df_gastos = carregar_dados_gastos()
    df_divida = carregar_dados_divida()

if not df_gastos.empty and not df_divida.empty:
    
    tab1, tab2, tab3 = st.tabs(["📊 Gastos (2025)", "📈 Dívida (Histórico)", "🧠 Análises Avançadas"])
    
    with tab1:
        st.header("Raio-X dos Gastos Públicos")
        
        st.info("ℹ️ **Nota:** A barra 'Encargos Especiais' inclui o serviço da dívida (juros/amortização).")
        
        col1, col2 = st.columns(2)
        if 'Funcao' in df_gastos.columns:
            funcoes = sorted(list(df_gastos['Funcao'].unique()))
            sel_funcao = col1.selectbox("Filtrar Função:", ['Todas'] + funcoes)
            
            if sel_funcao != 'Todas':
                df_view = df_gastos[df_gastos['Funcao'] == sel_funcao]
                # Se filtrou, mostra detalhe (Unidade)
                group_col = 'Unidade_Orcamentaria'
                title_chart = f"Top 10 Unidades em {sel_funcao}"
            else:
                df_view = df_gastos
                # Se é Geral, mostra Macro (Função) -> ISSO CORRIGE O GRÁFICO CONFUSO
                group_col = 'Funcao'
                title_chart = "Top 10 Funções do Orçamento (Visão Geral)"
                
            top_10 = df_view.groupby(group_col)['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(top_10.index, top_10.values, color='#0072B2')
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
            ax.grid(axis='x', linestyle='--', alpha=0.3)
            ax.set_title(title_chart)
            st.pyplot(fig)
            
            with st.expander("Ver Tabela Detalhada"):
                st.dataframe(df_view)
        else:
            st.error("Erro: Coluna de Função não identificada.")

    with tab2:
        st.header("Trajetória da Dívida Pública")
        
        if 'Data' in df_divida.columns:
            df_divida = df_divida.sort_values(by='Data')
            # Agrupa por data para somar tudo daquele mês
            df_linha = df_divida.groupby('Data')['Valor_Estoque'].sum()
            
            if not df_linha.empty:
                fig2, ax2 = plt.subplots(figsize=(10, 5))
                ax2.plot(df_linha.index, df_linha.values, color='#D55E00', linewidth=2)
                ax2.yaxis.set_major_formatter(ticker.FuncFormatter(format_tri))
                ax2.set_title("Evolução do Estoque Total")
                ax2.grid(True, linestyle='--', alpha=0.3)
                st.pyplot(fig2)
                
                ultima = df_linha.iloc[-1]
                data_ult = df_linha.index[-1]
                st.metric(f"Estoque em {data_ult.strftime('%m/%Y')}", f"R$ {ultima*1e-12:.2f} Trilhões")
            else:
                st.warning("Dados insuficientes para o gráfico.")
        else:
            st.error("Erro: Coluna de Data não identificada.")

    with tab3:
        st.header("Inteligência de Dados")
        opcoes = ["Selecione...", "📉 Análise de Concentração (Regra de Pareto)", "⚖️ Índice de Sustentabilidade (Dívida vs. Orçamento)", "📋 Listagem dos Gastos (Maior para Menor + %)", "🏦 Listagem dos Credores (Maior para Menor + %)"]
        escolha = st.selectbox("Execute um modelo de análise:", opcoes)
        if escolha != "Selecione...":
            st.markdown("---")
            st.markdown(gerar_insight_avancado(escolha, df_gastos, df_divida))

else:
    st.error("Erro crítico: Verifique os arquivos CSV no GitHub.")
