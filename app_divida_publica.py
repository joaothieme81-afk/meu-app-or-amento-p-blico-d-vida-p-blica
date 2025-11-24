# -*- coding: utf-8 -*-
"""
Aplicativo Streamlit (v6.1 - Finalíssimo)
Correção robusta de leitura de arquivos (UTF-8 e Latin-1)
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

# --- FUNÇÕES AUXILIARES DE LIMPEZA ---

def normalizar_colunas(df):
    """Remove acentos e espaços dos nomes das colunas para padronizar."""
    novas_colunas = {}
    for col in df.columns:
        nfkd_form = unicodedata.normalize('NFKD', col)
        sem_acento = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
        novo_nome = sem_acento.lower().strip().replace(' ', '_')
        novas_colunas[col] = novo_nome
    return df.rename(columns=novas_colunas)

def ler_csv_seguro(arquivo):
    """Tenta ler o CSV com diferentes encodings."""
    try:
        return pd.read_csv(arquivo, sep=';', encoding='utf-8')
    except (UnicodeDecodeError, pd.errors.ParserError):
        try:
            return pd.read_csv(arquivo, sep=';', encoding='latin1')
        except Exception as e:
            st.error(f"Erro crítico ao ler {arquivo}: {e}")
            return None
    except FileNotFoundError:
        # Tenta nomes alternativos caso o usuário não tenha renomeado
        alternativos = {
            "gastos_orcamento_2025.csv": "2025_OrcamentoDespesa.csv",
            "divida_estoque_historico.csv": "estoquedpf (1).csv"
        }
        if arquivo in alternativos:
            try:
                return ler_csv_seguro(alternativos[arquivo])
            except:
                pass
        st.error(f"ARQUIVO NÃO ENCONTRADO: '{arquivo}'. Verifique se o nome no GitHub está correto.")
        return None

# --- 1. CARREGAMENTO DE DADOS (BLINDADO) ---

@st.cache_data(ttl=3600)
def carregar_dados_gastos():
    df = ler_csv_seguro("gastos_orcamento_2025.csv")
    if df is None: return pd.DataFrame()
            
    df = normalizar_colunas(df)
    
    # Mapeamento flexível
    col_map = {
        'funcao': next((c for c in df.columns if 'funcao' in c and 'sub' not in c), None),
        'orgao_superior': next((c for c in df.columns if 'superior' in c), None),
        'unidade_orcamentaria': next((c for c in df.columns if 'unidade' in c), None),
        'valor': next((c for c in df.columns if 'realizado' in c or 'pago' in c), None)
    }
    
    # Se não achar as colunas essenciais, retorna vazio
    if not col_map['funcao'] or not col_map['valor']:
        st.error("Colunas essenciais (Função ou Valor) não encontradas no arquivo de gastos.")
        return pd.DataFrame()

    df = df.rename(columns={
        col_map['funcao']: 'Funcao',
        col_map['orgao_superior']: 'Orgao_Superior',
        col_map['unidade_orcamentaria']: 'Unidade_Orcamentaria',
        col_map['valor']: 'Valor_Realizado'
    })
    
    # Limpeza numérica
    df['Valor_Realizado'] = df['Valor_Realizado'].astype(str)
    df['Valor_Realizado'] = df['Valor_Realizado'].str.replace('.', '', regex=False)
    df['Valor_Realizado'] = df['Valor_Realizado'].str.replace(',', '.', regex=False)
    df['Valor_Realizado'] = pd.to_numeric(df['Valor_Realizado'], errors='coerce')
    return df.dropna(subset=['Valor_Realizado'])

@st.cache_data(ttl=3600)
def carregar_dados_divida():
    df = ler_csv_seguro("divida_estoque_historico.csv")
    if df is None: return pd.DataFrame()

    df = normalizar_colunas(df)
    
    col_map = {
        'data': next((c for c in df.columns if 'mes' in c or 'data' in c), None),
        'tipo': next((c for c in df.columns if 'tipo' in c), None),
        'valor': next((c for c in df.columns if 'valor' in c), None),
        'detentor': next((c for c in df.columns if 'detentor' in c), None)
    }
    
    if not col_map['data'] or not col_map['valor']:
        st.error("Colunas essenciais (Data ou Valor) não encontradas no arquivo da dívida.")
        return pd.DataFrame()
    
    rename_dict = {col_map['data']: 'Data', col_map['valor']: 'Valor_Estoque'}
    if col_map['tipo']: rename_dict[col_map['tipo']] = 'Tipo_Divida'
    if col_map['detentor']: rename_dict[col_map['detentor']] = 'Detentor'
    
    df = df.rename(columns=rename_dict)
    
    # Tratamento de Data
    df['Data'] = df['Data'].astype(str).str.strip()
    try:
        df['Data'] = pd.to_datetime(df['Data'], format='%m/%Y')
    except:
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    
    df = df.dropna(subset=['Data'])
    df['Ano'] = df['Data'].dt.year

    # Limpeza numérica
    df['Valor_Estoque'] = df['Valor_Estoque'].astype(str)
    df['Valor_Estoque'] = df['Valor_Estoque'].str.replace('.', '', regex=False)
    df['Valor_Estoque'] = df['Valor_Estoque'].str.replace(',', '.', regex=False)
    df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce')
    return df.dropna(subset=['Valor_Estoque'])

# --- 2. CÉREBRO DE ANÁLISE (COM EXPLICAÇÕES NOVAS) ---

def gerar_insight_avancado(pergunta, df_gastos, df_divida):
    try:
        if "Pareto" in pergunta:
            df_funcoes = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total_gasto = df_funcoes.sum()
            
            if total_gasto == 0: return "Dados zerados."
            
            df_acumulado = df_funcoes.cumsum()
            df_perc = (df_acumulado / total_gasto) * 100
            funcoes_80 = df_perc[df_perc <= 80].count() + 1
            total_funcoes = len(df_funcoes)
            top_1 = df_funcoes.index[0]
            top_1_perc = (df_funcoes.iloc[0] / total_gasto) * 100

            res = "### 📉 Análise de Concentração (Regra de Pareto)\n\n"
            res += f"- **Resultado:** Apenas **{funcoes_80} funções** (de {total_funcoes}) concentram **80%** do orçamento.\n"
            res += f"- **Maior Foco:** A função **{top_1}** consome **{top_1_perc:.1f}%** do total.\n\n"
            res += "--- \n"
            res += "**💡 Entenda o Conceito:**\n"
            res += "A Regra de Pareto (ou Princípio 80/20) afirma que, em muitos fenômenos, 80% das consequências vêm de 20% das causas. "
            res += "Aplicado ao orçamento público, isso demonstra uma alta **rigidez e concentração**: a grande maioria dos recursos do país está comprometida com pouquíssimas áreas (geralmente Dívida e Previdência), deixando pouco espaço para investimentos em outros setores."
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
            if df_divida.empty: return "Sem dados."
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
                res += "**Nota:** Dados detalhados por credor não encontrados no CSV histórico. Exibindo por Tipo.\n\n"
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
        
        # NOVA MENSAGEM EXPLICATIVA
        st.info("""
        ℹ️ **Entenda os dados:** A categoria **"Encargos Especiais"** (frequentemente a maior barra do gráfico) 
        representa majoritariamente o **Serviço da Dívida Pública** (refinanciamento, amortização e juros) 
        e outras transferências constitucionais obrigatórias. Ela não reflete o custo operacional da máquina pública (salários, luz, etc.), 
        mas sim os compromissos financeiros do Estado.
        """)
        
        col1, col2 = st.columns(2)
        if 'Funcao' in df_gastos.columns:
            funcoes = sorted(list(df_gastos['Funcao'].unique()))
            sel_funcao = col1.selectbox("Filtrar Função:", ['Todas'] + funcoes)
            
            if sel_funcao != 'Todas':
                df_view = df_gastos[df_gastos['Funcao'] == sel_funcao]
                group_col = 'Unidade_Orcamentaria'
                title_chart = f"Top 10 Unidades em {sel_funcao}"
            else:
                df_view = df_gastos
                group_col = 'Funcao'
                title_chart = "Top 10 Funções do Orçamento"
                
            top_10 = df_view.groupby(group_col)['Valor_Realizado'].sum().nlargest(10).sort_values(ascending=True)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(top_10.index, top_10.values, color='#0072B2')
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
            ax.grid(axis='x', linestyle='--', alpha=0.3)
            ax.set_title(title_chart)
            st.pyplot(fig)
            
            with st.expander("Ver Tabela"):
                st.dataframe(df_view)
        else:
            st.error("Erro: Coluna de Função não identificada.")

    with tab2:
        st.header("Trajetória da Dívida Pública")
        
        if 'Data' in df_divida.columns:
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
