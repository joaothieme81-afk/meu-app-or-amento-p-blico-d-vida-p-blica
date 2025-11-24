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
    page_icon="📊",
    layout="wide"
)

# --- 1. FUNÇÕES UTILITÁRIAS ---

@st.cache_data
def carregar_csv(url):
    try:
        df = pd.read_csv(url, sep=';', encoding='utf-8', decimal=',')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar CSV de {url}: {e}")
        return pd.DataFrame()

# Função para traduzir datas em português (ex.: "jan/23", "fev/2024")
def traduzir_data_pt_br(data_str):
    if pd.isna(data_str):
        return None

    data_str = str(data_str).strip().lower()

    meses = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }

    try:
        # Ex: "jan/23" ou "jan/2023"
        if '/' in data_str:
            parte_mes = data_str.split('/')[0][:3]
            parte_ano = data_str.split('/')[1]

            if parte_mes not in meses:
                return None

            mes_num = meses[parte_mes]

            # Ano em 2 dígitos -> converte para 4 (assumindo 20xx)
            if len(parte_ano) == 2:
                ano_num = int(parte_ano)
                ano_full = 2000 + ano_num
            else:
                ano_full = int(parte_ano)

            data_fmt = f"{ano_full}-{mes_num}-01"
            return pd.to_datetime(data_fmt, format="%Y-%m-%d")

        # Se vier só o ano, tipo "2023"
        if len(data_str) == 4 and data_str.isdigit():
            return pd.to_datetime(f"{data_str}-01-01", format="%Y-%m-%d")

        return None
    except Exception:
        return None

# Carregamento dos dados
URL_GASTOS = "https://raw.githubusercontent.com/leticiafgvbr/dados_gastos_publicos/main/gastos_funcao_2025.csv"
URL_DIVIDA = "https://raw.githubusercontent.com/leticiafgvbr/dados_gastos_publicos/main/divida_estoque_historico.csv"

df_gastos_bruto = carregar_csv(URL_GASTOS)
df_divida_bruto = carregar_csv(URL_DIVIDA)

def preparar_gastos(df):
    if df.empty:
        return df

    # Garante colunas essenciais
    col_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    col_ano = 'Ano'
    col_funcao = 'Funcao'

    for col in col_meses + [col_ano, col_funcao]:
        if col not in df.columns:
            st.error(f"Coluna obrigatória faltando nos gastos: {col}")
            return pd.DataFrame()

    # Transforma em formato longo (tidy): uma linha por função/mês
    df_long = df.melt(
        id_vars=[col_ano, col_funcao],
        value_vars=col_meses,
        var_name='Mes',
        value_name='Valor'
    )

    # Conversão de valor para numérico
    df_long['Valor'] = (
        df_long['Valor']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df_long['Valor'] = pd.to_numeric(df_long['Valor'], errors='coerce').fillna(0)

    # Monta uma coluna de Data (primeiro dia de cada mês)
    mapa_mes = {
        'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4,
        'Mai': 5, 'Jun': 6, 'Jul': 7, 'Ago': 8,
        'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12
    }
    df_long['Mes_Num'] = df_long['Mes'].map(mapa_mes)
    df_long['Data'] = pd.to_datetime(
        dict(year=df_long[col_ano], month=df_long['Mes_Num'], day=1),
        errors='coerce'
    )

    df_long = df_long.rename(columns={col_funcao: 'Funcao', col_ano: 'Ano'})
    df_long['Valor_Realizado'] = df_long['Valor']
    return df_long

def preparar_divida(df):
    if df.empty:
        return df

    # Verifica coluna de data original (Mes do Estoque)
    col_data = None
    for c in df.columns:
        if 'Mes do Estoque' in c or 'Mes_do_Estoque' in c or 'Mes_Estoque' in c:
            col_data = c
            break

    if col_data is None:
        st.error("Não foi encontrada coluna de mês/estoque na base da dívida.")
        return pd.DataFrame()

    df = df.copy()
    df['Data_Original'] = df[col_data]

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
        df['Valor_Estoque'] = pd.to_numeric(df['Valor_Estoque'], errors='coerce').fillna(0)
    else:
        # Tenta procurar algo semelhante
        possiveis = [c for c in df.columns if 'Valor' in c or 'Estoque' in c]
        if possiveis:
            df['Valor_Estoque'] = pd.to_numeric(
                df[possiveis[0]]
                .astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False),
                errors='coerce'
            ).fillna(0)
        else:
            st.error("Nenhuma coluna de valor da dívida encontrada.")
            return pd.DataFrame()

    # Renomeia colunas de tipo/espécie de dívida, se existirem
    for c in df.columns:
        if 'Tipo_Divida' in c or 'Tipo de Dívida' in c:
            df = df.rename(columns={c: 'Tipo_Divida'})
        if 'Detentor' in c or 'Credor' in c:
            df = df.rename(columns={c: 'Detentor'})

    return df

df_gastos = preparar_gastos(df_gastos_bruto)
df_divida = preparar_divida(df_divida_bruto)

# --- 2. MÓDULOS DE ANÁLISE ---

def gerar_insight_avancado(pergunta, df_gastos, df_divida):
    try:
        if "Pareto" in pergunta:
            df_funcoes = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
            total_gasto = df_funcoes.sum()
            
            if total_gasto == 0:
                return "Dados de gastos zerados."

            df_acumulado = df_funcoes.cumsum()
            df_perc = (df_acumulado / total_gasto) * 100
            funcoes_80 = df_perc[df_perc <= 80].count() + 1
            total_funcoes = len(df_funcoes)
            
            top_1 = df_funcoes.index[0]
            top_1_perc = (df_funcoes.iloc[0] / total_gasto) * 100
            
            res = "### 📉 Aplicando a Regra de Pareto aos Gastos Públicos (2025)\n\n"
            res += f"- Número total de funções orçamentárias: **{total_funcoes}**.\n"
            res += f"- Quantidade aproximada de funções responsáveis por até 80% do gasto total: **{funcoes_80}**.\n"
            res += f"- A função que mais consome recursos é **{top_1}**, absorvendo cerca de **{top_1_perc:.1f}%** do total.\n\n"
            res += "--- \n**💡 O que isso significa?**\n"
            res += "A Regra de Pareto (80/20) aplicada aqui mostra que uma minoria de funções concentra a maior parte do orçamento, "
            res += "o que levanta questões sobre prioridades de gasto, transparência e a necessidade de avaliação de políticas públicas "
            res += "que consomem montantes muito significativos, deixando relativamente poucos recursos para as outras dezenas de funções do Estado."
            return res
            
        elif "Sustentabilidade" in pergunta:
            if df_divida.empty:
                return "Dados de dívida insuficientes."
            data_max = df_divida['Data'].max()
            divida_total = df_divida[df_divida['Data'] == data_max]['Valor_Estoque'].sum()
            gasto_total_anual = df_gastos['Valor_Realizado'].sum()
            
            if gasto_total_anual > 0:
                razao = divida_total / gasto_total_anual
                anos_estimados = razao
                res = "### ⚖️ Índice de Sustentabilidade da Dívida\n\n"
                res += f"- **Estoque Total da Dívida (último dado: {data_max.strftime('%m/%Y')}):** R$ {divida_total*1e-12:.2f} trilhões.\n"
                res += f"- **Total de Gastos Orçamentários Anuais (2025):** R$ {gasto_total_anual*1e-12:.2f} trilhões.\n"
                res += f"- **Relação Dívida / Gasto Anual:** a dívida corresponde a aproximadamente **{razao:.1f} vezes** o gasto de um ano.\n\n"
                res += "--- \n**💡 Interpretação:**\n"
                res += "Se imaginarmos, de forma simplificada, que todo o gasto anual pudesse ser direcionado apenas para pagar dívida, "
                res += f"seriam necessários cerca de **{anos_estimados:.1f} anos** para quitá-la. Isso reforça a importância de um debate "
                res += "sobre trajetória da dívida, taxa de juros e espaço fiscal para políticas públicas."
                return res
            else:
                return "Não foi possível calcular: gastos anuais zerados ou inválidos."
            
        elif "Listagem dos Gastos" in pergunta:
            df_agg = df_gastos.groupby('Funcao')['Valor_Realizado'].sum()
            df_rank = df_agg.sort_values(ascending=False)
            total = df_rank.sum()
            res = "### 📋 Ranking de Gastos por Função (2025)\n\n"
            for func, valor in df_rank.items():
                perc = (valor / total) * 100
                if perc > 0.1:  # Filtra os muito pequenos
                    res += f"1. **{func}**: R$ {valor*1e-9:.1f} bi (**{perc:.1f}%**)\n"
            return res

        return "Selecione uma análise."
    except Exception as e:
        return f"Erro no cálculo: {e}"

# --- 3. INTERFACE GRÁFICA ---

def format_bi(x, pos):
    return f'R$ {x*1e-9:.0f} bi'

def format_tri(x, pos):
    return f'R$ {x*1e-12:.1f} T'

st.title("Análise Orçamentária do Brasil 🇧🇷")
st.markdown("Ferramenta de fiscalização baseada em dados oficiais do orçamento e da dívida pública federal.")

if not df_gastos.empty and not df_divida.empty:

    tab1, tab2, tab3 = st.tabs(["📊 Gastos por Função", "💰 Dívida Pública (Histórico)", "🧠 Análises Interativas"])

    with tab1:
        st.header("Evolução dos Gastos por Função (2025)")

        funcoes_disponiveis = df_gastos['Funcao'].unique().tolist()
        
        col_esq, col_dir = st.columns([2, 1])

        with col_esq:
            funcao_selecionada = st.selectbox(
                "Selecione uma função para detalhar (ou deixe 'Geral' para todos):",
                options=["Geral"] + sorted(funcoes_disponiveis)
            )

        with col_dir:
            tipo_grafico = st.radio(
                "Tipo de visualização:",
                options=["Linha - Total Mensal", "Barras - Comparação de Funções"],
                index=0
            )

        if funcao_selecionada == "Geral":
            df_total_mes = df_gastos.groupby('Data')['Valor_Realizado'].sum()
            df_total_mes = df_total_mes.sort_index()

            if tipo_grafico == "Linha - Total Mensal":
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df_total_mes.index, df_total_mes.values, marker='o')
                ax.set_title("Gasto Total do Orçamento Federal por Mês (2025)")
                ax.set_ylabel("R$ (em bilhões)")
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
                ax.grid(True, linestyle='--', alpha=0.3)
                st.pyplot(fig)
            else:
                df_funcao = df_gastos.groupby('Funcao')['Valor_Realizado'].sum().sort_values(ascending=False)
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.bar(df_funcao.index, df_funcao.values)
                ax.set_title("Gasto Total por Função (2025)")
                ax.set_ylabel("R$ (em bilhões)")
                ax.set_xticklabels(df_funcao.index, rotation=45, ha='right')
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
                st.pyplot(fig)
        else:
            df_filtrado = df_gastos[df_gastos['Funcao'] == funcao_selecionada]
            df_filtrado = df_filtrado.groupby('Data')['Valor_Realizado'].sum().sort_index()

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_filtrado.index, df_filtrado.values, marker='o')
            ax.set_title(f"Gastos da Função: {funcao_selecionada} (2025)")
            ax.set_ylabel("R$ (em bilhões)")
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_bi))
            ax.grid(True, linestyle='--', alpha=0.3)
            st.pyplot(fig)

            total_func = df_filtrado.sum()
            total_geral = df_gastos['Valor_Realizado'].sum()
            perc = (total_func / total_geral * 100) if total_geral > 0 else 0
            st.metric("Participação no Orçamento Anual (2025)", f"{perc:.1f}%")

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
                st.metric(
                    f"Estoque em {data_ult.strftime('%m/%Y')}",
                    f"R$ {ultima*1e-12:.2f} Trilhões"
                )

                # 🔹 Texto explicativo sobre o conceito de dívida
                st.markdown("""
                **Como interpretar este gráfico**

                - Os valores representam o **estoque total da dívida pública federal** na base utilizada, somando diferentes modalidades de títulos e contratos.
                - Esse conceito é **mais amplo** do que a Dívida Pública Federal “em mercado”, que costuma aparecer na mídia na faixa de **R$ 6–8 trilhões**. Aqui, o estoque inclui componentes adicionais e diferentes detentores da dívida.
                - A base diferencia **dívida interna** (títulos emitidos em reais, em geral colocados no mercado doméstico) e **dívida externa** (títulos e contratos em moeda estrangeira). O gráfico, porém, mostra o **total agregado** dessas duas parcelas.

                Em síntese, o foco desta visualização é a **trajetória do estoque total da dívida pública**, e não apenas a parcela negociada em mercado.
                """)
            else:
                st.warning("Dados insuficientes para o gráfico.")
        else:
            st.error("Erro: Coluna de Data não identificada.")

    with tab3:
        st.header("Inteligência de Dados")
        opcoes = [
            "Selecione...",
            "📉 Análise de Concentração (Regra de Pareto)",
            "⚖️ Índice de Sustentabilidade (Dívida vs. Orçamento)",
            "📋 Listagem dos Gastos (Maior para Menor + %)",
        ]
        escolha = st.selectbox("Execute um modelo de análise:", opcoes)
        if escolha != "Selecione...":
            st.markdown("---")
            st.markdown(gerar_insight_avancado(escolha, df_gastos, df_divida))

else:
    st.error("Erro crítico: Verifique os arquivos CSV no GitHub.")




