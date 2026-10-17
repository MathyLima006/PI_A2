from pathlib import Path
import re
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="SITCON | Inventário",
    page_icon="🚆",
    layout="wide"
)

PASTA = Path(__file__).parent

ARQUIVO_SINAIS = PASTA / "levantamento BD Sinais via 1 e 2.xlsx"
ARQUIVO_CDVS = PASTA / "levantamento BD CDVs via 1 e 2.xlsx"

CORES = ["#2878B5", "#36A18B", "#E5A84B", "#8C79B8", "#D46A6A"]


# =========================================================
# FUNÇÕES DE TRATAMENTO
# =========================================================

def limpar(valor):
    if pd.isna(valor):
        return None

    valor = re.sub(r"\s+", " ", str(valor)).strip()

    if not valor or valor.lower() in {"nan", "none", "nat"}:
        return None

    if valor in {"-", "—", "–"}:
        return None

    return valor


def eh_titulo(valor, prefixo):
    valor = limpar(valor)
    return bool(valor and valor.upper().startswith(prefixo))


def carregar_planilha(caminho):
    return pd.read_excel(caminho, header=None, dtype=object)


def extrair_sinais(planilha):
    registros = []
    linhas, colunas = planilha.shape
    titulos = []

    for linha in range(linhas):
        for coluna in range(colunas):
            valor = limpar(planilha.iat[linha, coluna])

            if valor and re.match(r"^SINAL\s+\d+\b", valor.upper()):
                titulos.append((
                    linha,
                    coluna,
                    valor
                ))


    for linha_titulo, coluna_inicio, nome in titulos:
        proximos = [
            linha for linha, coluna, _ in titulos
            if coluna == coluna_inicio and linha > linha_titulo
        ]

        fim = min(proximos) if proximos else linhas
        colunas_ids = range(
            coluna_inicio + 1,
            min(coluna_inicio + 5, colunas)
        )

        for linha in range(linha_titulo + 4, fim):
            local = limpar(planilha.iat[linha, coluna_inicio])

            if not local:
                continue

            if local.upper().startswith("SINAL"):
                continue

            if local.lower().startswith("sinaleiro"):
                continue

            for posicao, coluna_id in enumerate(colunas_ids, start=1):
                identificador = limpar(planilha.iat[linha, coluna_id])

                registros.append({
                    "tipo": "Sinal luminoso",
                    "equipamento": nome,
                    "localizacao": local,
                    "funcao": f"Identificação {posicao}",
                    "identificador": identificador,
                    "linha_planilha": linha + 1
                })

    return pd.DataFrame(registros)


def extrair_cdvs(planilha):
    registros = []
    linhas, colunas = planilha.shape
    titulos = []

    for linha in range(linhas):
        for coluna in range(colunas):
            if eh_titulo(planilha.iat[linha, coluna], "CDV"):
                titulos.append((
                    linha,
                    coluna,
                    limpar(planilha.iat[linha, coluna])
                ))

    for linha_titulo, coluna_inicio, nome in titulos:
        proximos = [
            linha for linha, coluna, _ in titulos
            if coluna == coluna_inicio and linha > linha_titulo
        ]

        fim = min(proximos) if proximos else linhas
        colunas_funcoes = range(
            coluna_inicio + 1,
            min(coluna_inicio + 6, colunas)
        )

        for linha in range(linha_titulo + 1, fim):
            local = limpar(planilha.iat[linha, coluna_inicio])

            if not local or local.upper().startswith("CDV"):
                continue

            if local.lower() in {
                "localização", "localizacao",
                "codificação", "codificacao",
                "funções", "funcoes",
                "indicação", "indicacao"
            }:
                continue

            for coluna_id in colunas_funcoes:
                identificador = limpar(planilha.iat[linha, coluna_id])

                candidatos = [
                    limpar(planilha.iat[cabecalho, coluna_id])
                    for cabecalho in range(
                        linha_titulo + 1,
                        min(linha_titulo + 4, linhas)
                    )
                ]

                candidatos = [
                    item for item in candidatos
                    if item and item.lower() not in {
                        "localização", "localizacao",
                        "codificação", "codificacao",
                        "funções", "funcoes",
                        "indicação", "indicacao"
                    }
                ]

                funcao = (
                    candidatos[-1]
                    if candidatos
                    else f"Função {coluna_id - coluna_inicio}"
                )

                registros.append({
                    "tipo": "Circuito de via (CDV)",
                    "equipamento": nome,
                    "localizacao": local,
                    "funcao": funcao,
                    "identificador": identificador,
                    "linha_planilha": linha + 1
                })

    return pd.DataFrame(registros)


def classificar_local(local):
    texto = str(local).lower()

    if "locação" in texto or "locacao" in texto:
        return "Locações"
    if "armário" in texto or "armario" in texto:
        return "Armários"
    if "interface" in texto:
        return "Interfaces"
    if "sinaleiro" in texto:
        return "Sinaleiros"

    return "Outros"


def numero(valor):
    return f"{valor:,}".replace(",", ".")


def grafico_barras(dados, x, y, titulo, cor=None, altura=400):
    fig = px.bar(
        dados,
        x=x,
        y=y,
        color=cor,
        orientation="h" if y else "v",
        color_discrete_sequence=CORES,
        title=titulo
    )

    fig.update_layout(
        height=altura,
        margin=dict(l=10, r=20, t=55, b=10),
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        template="plotly_white"
    )

    return fig

    

# =========================================================
# CARREGAMENTO AUTOMÁTICO DAS PLANILHAS
# =========================================================

st.title("🚆 SITCON")
st.caption("Painel de análise do inventário de sinalização ferroviária")

try:
    sinais_raw = carregar_planilha(ARQUIVO_SINAIS)
    cdvs_raw = carregar_planilha(ARQUIVO_CDVS)

    sinais = extrair_sinais(sinais_raw)
    cdvs = extrair_cdvs(cdvs_raw)

except FileNotFoundError as erro:
    st.error(f"Arquivo não encontrado: {erro.filename}")
    st.stop()

except Exception as erro:
    st.error(f"Erro ao carregar as planilhas: {erro}")
    st.stop()

if sinais.empty and cdvs.empty:
    st.error("Não foram encontrados registros nas planilhas.")
    st.stop()

dados = pd.concat([sinais, cdvs], ignore_index=True)

dados["tipo_local"] = dados["localizacao"].apply(classificar_local)

# Registros com identificador preenchido.
preenchidos = dados[dados["identificador"].notna()].copy()

# Não removemos repetições automaticamente:
# elas precisam ser investigadas, não presumidas como erros.

# =========================================================
# NAVEGAÇÃO
# =========================================================

st.sidebar.title("🚆 SITCON")

pagina = st.sidebar.radio(
    "Navegação",
    [
        "Visão Geral",
        "Explorar Dados",
        "Qualidade dos Dados"
    ]
)



# PÁGINA 1 — VISÃO GERAL
if pagina == "Visão Geral":
    st.header("Visão Geral do Inventário")
    st.write(
        "Resumo das informações disponíveis nas planilhas "
        "de sinais luminosos e circuitos de via (CDVs)."
    )

    # 1. INDICADORES PRINCIPAIS
    grupos_sinais = (
        sinais.loc[sinais["identificador"].notna(), "equipamento"].nunique()
        if not sinais.empty else 0
    )

    grupos_cdvs = (
        cdvs.loc[cdvs["identificador"].notna(), "equipamento"].nunique()
        if not cdvs.empty else 0
    )

    total_preenchidos = int(dados["identificador"].notna().sum())
    ids_distintos = int(preenchidos["identificador"].nunique())

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Grupos de sinais", numero(grupos_sinais))
    c2.metric("Grupos de CDVs", numero(grupos_cdvs))
    c3.metric("Identificadores preenchidos", numero(total_preenchidos))
    c4.metric("Identificadores distintos", numero(ids_distintos))

    st.divider()

    # 2. COMPARAÇÃO ENTRE SINAIS E CDVs
    st.subheader("Identificadores por tipo de equipamento")

    comparacao = pd.DataFrame({
        "Tipo de equipamento": [
            "Sinais luminosos",
            "Circuitos de via (CDVs)"
        ],
        "Identificadores preenchidos": [
            int(sinais["identificador"].notna().sum()),
            int(cdvs["identificador"].notna().sum())
        ]
    })

    fig = px.bar(
        comparacao,
        x="Tipo de equipamento",
        y="Identificadores preenchidos",
        color="Tipo de equipamento",
        text="Identificadores preenchidos",
        color_discrete_sequence=CORES
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=330,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=20, r=20, t=25, b=20),
        xaxis_title=None,
        yaxis_title="Quantidade de identificadores"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )

    st.caption(
        "A comparação mostra quantos identificadores preenchidos "
        "foram extraídos de cada planilha. Isso não representa "
        "necessariamente a quantidade de equipamentos físicos únicos."
    )

    st.divider()

    # 3. DISTRIBUIÇÃO POR LOCALIZAÇÃO
    st.subheader("Localizações com mais identificadores cadastrados")

    comparacao_local = (
        preenchidos
        .groupby(["localizacao", "tipo"])
        .size()
        .reset_index(name="Quantidade")
    )

    principais_locais = (
        preenchidos
        .groupby("localizacao")
        .size()
        .nlargest(12)
        .index
    )

    comparacao_local = comparacao_local[
        comparacao_local["localizacao"].isin(principais_locais)
    ]

    if not comparacao_local.empty:
        fig = px.bar(
            comparacao_local,
            x="Quantidade",
            y="localizacao",
            color="tipo",
            barmode="group",
            orientation="h",
            color_discrete_sequence=CORES
        )

        fig.update_layout(
            height=450,
            template="plotly_white",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Identificadores preenchidos",
            yaxis_title=None,
            legend_title="Tipo de equipamento",
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )
    else:
        st.info("Não há identificadores preenchidos para exibir por localização.")

    st.caption(
        "São exibidas as 12 localizações com maior quantidade de "
        "identificadores preenchidos, separadas por tipo de equipamento."
    )

    st.divider()

    # 4. DISTRIBUIÇÃO POR CATEGORIA DE LOCALIZAÇÃO
    st.subheader("Distribuição por categoria de localização")

    distribuicao = (
        preenchidos
        .groupby("tipo_local")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )

    if not distribuicao.empty:
        fig = px.bar(
            distribuicao,
            x="tipo_local",
            y="Quantidade",
            color="tipo_local",
            text="Quantidade",
            color_discrete_sequence=CORES
        )

        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=350,
            template="plotly_white",
            showlegend=False,
            margin=dict(l=20, r=20, t=25, b=20),
            xaxis_title="Categoria",
            yaxis_title="Identificadores preenchidos"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )
    else:
        st.info("Não há dados preenchidos para classificar por categoria.")

    st.caption(
        "As categorias são estimadas pelo programa com base nos textos "
        "das planilhas. Confira a classificação na página de exploração "
        "dos dados quando necessário."
    )

    st.divider()

    # 5. COMPLETUDE DO INVENTÁRIO
    st.subheader("Completude do inventário")

    total_posicoes = len(dados)
    posicoes_preenchidas = int(dados["identificador"].notna().sum())

    percentual = (
        posicoes_preenchidas / total_posicoes * 100
        if total_posicoes else 0
    )

    c1, c2 = st.columns([1, 3])

    c1.metric("Preenchimento", f"{percentual:.1f}%")
    c2.progress(percentual / 100)
    c2.caption(
        f"{numero(posicoes_preenchidas)} de "
        f"{numero(total_posicoes)} posições extraídas possuem identificador."
    )

    st.caption(
        "O percentual considera as posições extraídas pelo programa, "
        "não necessariamente todos os campos existentes nas planilhas originais."
    )



# =========================================================
# PÁGINA 2 — EXPLORAÇÃO DOS DADOS
# =========================================================

if pagina == "Explorar Dados":
    st.header("Exploração dos Dados")
    st.write(
        "Pesquise, filtre e consulte os registros extraídos "
        "das planilhas de sinalização ferroviária."
    )

    # FILTROS
    st.subheader("Filtros de pesquisa")

    col1, col2 = st.columns(2)

    with col1:
        busca = st.text_input(
            "Pesquisar registro",
            placeholder="Digite identificador, equipamento, localização ou função..."
        )

    with col2:
        tipos_disponiveis = ["Todos"] + sorted(
            dados["tipo"].dropna().astype(str).unique().tolist()
        )

        tipo_selecionado = st.selectbox(
            "Tipo de equipamento",
            tipos_disponiveis
        )

    col3, col4 = st.columns(2)

    with col3:
        locais_disponiveis = ["Todos"] + sorted(
            dados["localizacao"].dropna().astype(str).unique().tolist()
        )

        local_selecionado = st.selectbox(
            "Localização",
            locais_disponiveis
        )

    with col4:
        situacao_id = st.selectbox(
            "Preenchimento do identificador",
            [
                "Todos",
                "Preenchido",
                "Não preenchido"
            ]
        )

    # APLICAÇÃO DOS FILTROS
    resultado = dados.copy()

    if tipo_selecionado != "Todos":
        resultado = resultado[
            resultado["tipo"].astype(str) == tipo_selecionado
        ]

    if local_selecionado != "Todos":
        resultado = resultado[
            resultado["localizacao"].astype(str) == local_selecionado
        ]

    if situacao_id == "Preenchido":
        resultado = resultado[
            resultado["identificador"].notna()
        ]
    elif situacao_id == "Não preenchido":
        resultado = resultado[
            resultado["identificador"].isna()
        ]

    if busca.strip():
        termo = busca.strip()

        colunas_busca = [
            "identificador",
            "equipamento",
            "localizacao",
            "funcao"
        ]

        mascara = resultado[colunas_busca].apply(
            lambda coluna: coluna.astype(str).str.contains(
                termo,
                case=False,
                na=False,
                regex=False
            )
        ).any(axis=1)

        resultado = resultado[mascara]

    st.divider()

    # RESUMO DA CONSULTA
    st.subheader("Resultados da consulta")

    total_resultados = len(resultado)
    total_ids = int(resultado["identificador"].notna().sum())
    total_sem_id = int(resultado["identificador"].isna().sum())

    m1, m2, m3 = st.columns(3)

    m1.metric("Registros encontrados", numero(total_resultados))
    m2.metric("Com identificador", numero(total_ids))
    m3.metric("Sem identificador", numero(total_sem_id))

    # TABELA DE RESULTADOS
    st.caption(
        "Os resultados respeitam os filtros selecionados. "
        "Nenhum registro é removido da base original."
    )

    colunas_tabela = [
        "tipo",
        "equipamento",
        "localizacao",
        "funcao",
        "identificador",
        "linha_planilha"
    ]

    tabela = resultado[colunas_tabela].copy()

    tabela = tabela.rename(columns={
        "tipo": "Tipo de equipamento",
        "equipamento": "Equipamento",
        "localizacao": "Localização",
        "funcao": "Função",
        "identificador": "Identificador",
        "linha_planilha": "Linha de origem"
    })

    tabela = tabela.fillna("Não informado")

    if tabela.empty:
        st.info(
            "Nenhum registro corresponde aos filtros selecionados. "
            "Tente alterar a pesquisa ou remover algum filtro."
        )
    else:
        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            height=500
        )

        # EXPORTAÇÃO DOS RESULTADOS FILTRADOS
        csv = tabela.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Baixar resultados em CSV",
            data=csv,
            file_name="exploracao_dados_sitcon.csv",
            mime="text/csv"
        )

# =========================================================
# PÁGINA 5 — QUALIDADE DOS DADOS
# =========================================================

elif pagina == "Qualidade dos Dados":

    st.header("Qualidade dos Dados")
    st.write(
        "Identifique informações ausentes e possíveis duplicidades "
        "para facilitar a conferência do inventário."
    )

    # Identificar campos vazios
    campos = [
        "tipo",
        "equipamento",
        "localizacao",
        "funcao",
        "identificador"
    ]

    tabela = dados.copy()

    for coluna in campos:
        tabela[coluna] = tabela[coluna].replace(
            r"^\s*$", pd.NA, regex=True
        )

    # Indicadores principais
    total_registros = len(tabela)
    sem_identificador = tabela["identificador"].isna().sum()

    ids = tabela["identificador"].astype("string").str.strip()
    ids_validos = ids.notna() & ids.ne("")

    mascara_repetidos = ids_validos & ids.duplicated(keep=False)
    total_repetidos = int(mascara_repetidos.sum())

    c1, c2, c3 = st.columns(3)

    c1.metric("Registros analisados", numero(total_registros))
    c2.metric("Sem identificador", numero(int(sem_identificador)))
    c3.metric("Registros com ID repetido", numero(total_repetidos))

    st.divider()

    # Campos ausentes
    st.subheader("Informações ausentes")

    ausentes = tabela[campos].isna().sum()

    resumo = pd.DataFrame({
        "Campo": ausentes.index,
        "Quantidade ausente": ausentes.values
    })

    resumo = resumo.sort_values(
        "Quantidade ausente",
        ascending=False
    )

    st.dataframe(
        resumo,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Registros sem identificador
    st.subheader("Registros sem identificador")

    sem_id = tabela["identificador"].isna()

    if sem_id.any():
        st.dataframe(
            tabela.loc[
                sem_id,
                [
                    "tipo",
                    "equipamento",
                    "localizacao",
                    "funcao",
                    "linha_planilha"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Todos os registros possuem identificador.")

    st.divider()

    
