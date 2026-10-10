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
            if eh_titulo(planilha.iat[linha, coluna], "SINAL"):
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
        "Análise dos Sinais",
        "Análise dos CDVs",
        "Qualidade dos Dados"
    ]
)

# =========================================================
# PÁGINA 1 — VISÃO GERAL
# =========================================================

if pagina == "Visão Geral":

    grupos_sinais = (
        sinais.loc[sinais["identificador"].notna(), "equipamento"].nunique()
        if not sinais.empty else 0
    )

    grupos_cdvs = (
        cdvs.loc[cdvs["identificador"].notna(), "equipamento"].nunique()
        if not cdvs.empty else 0
    )

    total_preenchidos = len(preenchidos)
    ids_distintos = preenchidos["identificador"].nunique()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Grupos de sinais", numero(grupos_sinais))
    c2.metric("Grupos de CDVs", numero(grupos_cdvs))
    c3.metric("Identificadores preenchidos", numero(total_preenchidos))
    c4.metric("Identificadores distintos", numero(ids_distintos))

    st.divider()

    esquerda, direita = st.columns(2, gap="large")

    with esquerda:
        st.subheader("Distribuição por tipo de localização")

        distribuicao = (
            preenchidos.groupby("tipo_local")
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )

        fig = px.pie(
            distribuicao,
            names="tipo_local",
            values="Quantidade",
            hole=0.58,
            color_discrete_sequence=CORES
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent"
        )

        fig.update_layout(
            height=390,
            margin=dict(l=10, r=10, t=20, b=10),
            legend_title=None
        )

        st.plotly_chart(fig, use_container_width=True)

    with direita:
        st.subheader("Sinais e CDVs por localização")

        comparacao = (
            preenchidos.groupby(["localizacao", "tipo"])
            .size()
            .reset_index(name="Quantidade")
        )

        principais = (
            preenchidos.groupby("localizacao")
            .size()
            .nlargest(12)
            .index
        )

        comparacao = comparacao[
            comparacao["localizacao"].isin(principais)
        ]

        fig = px.bar(
            comparacao,
            x="Quantidade",
            y="localizacao",
            color="tipo",
            barmode="group",
            orientation="h",
            color_discrete_sequence=CORES
        )

        fig.update_layout(
            height=390,
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_title="Identificadores cadastrados",
            yaxis_title=None,
            legend_title=None,
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()
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
        f"{numero(total_posicoes)} posições extraídas têm identificador."
    )

    st.caption(
        "A categoria de localização é estimada a partir do texto da planilha. "
        "A completude considera as posições extraídas pelo programa, "
        "não necessariamente todos os campos existentes no documento original."
    )


# =========================================================
# PÁGINA 2 — EXPLORAÇÃO INTERATIVA
# =========================================================

elif pagina == "Explorar Dados":

    st.subheader("Explorar o inventário")
    st.write(
        "Filtre os registros para comparar localizações, analisar funções "
        "e investigar identificadores repetidos ou campos não preenchidos."
    )

    # ---------------- Filtros ----------------

    st.sidebar.divider()
    st.sidebar.subheader("Filtros da exploração")

    tipos_disponiveis = sorted(preenchidos["tipo"].dropna().unique())

    tipos_selecionados = st.sidebar.multiselect(
        "Tipo de equipamento",
        tipos_disponiveis,
        default=tipos_disponiveis
    )

    filtrado = preenchidos[
        preenchidos["tipo"].isin(tipos_selecionados)
    ].copy()

    locais_disponiveis = sorted(filtrado["localizacao"].dropna().unique())

    locais_selecionados = st.sidebar.multiselect(
        "Localização",
        locais_disponiveis,
        default=locais_disponiveis
    )

    filtrado = filtrado[
        filtrado["localizacao"].isin(locais_selecionados)
    ].copy()

    equipamentos_disponiveis = sorted(
        filtrado["equipamento"].dropna().unique()
    )

    equipamentos_selecionados = st.sidebar.multiselect(
        "Grupo de equipamento",
        equipamentos_disponiveis,
        default=equipamentos_disponiveis
    )

    filtrado = filtrado[
        filtrado["equipamento"].isin(equipamentos_selecionados)
    ].copy()

    funcoes_disponiveis = sorted(filtrado["funcao"].dropna().unique())

    funcoes_selecionadas = st.sidebar.multiselect(
        "Função / identificação",
        funcoes_disponiveis,
        default=funcoes_disponiveis
    )

    filtrado = filtrado[
        filtrado["funcao"].isin(funcoes_selecionadas)
    ].copy()

    busca = st.text_input(
        "Pesquisar identificador ou texto",
        placeholder="Digite um código, localização ou equipamento..."
    )

    if busca.strip():
        mascara = filtrado.astype(str).apply(
            lambda coluna: coluna.str.contains(
                busca.strip(),
                case=False,
                na=False,
                regex=False
            )
        ).any(axis=1)

        filtrado = filtrado[mascara].copy()

    if filtrado.empty:
        st.warning("Nenhum resultado. Altere os filtros ou a pesquisa.")
        st.stop()

    # ---------------- Indicadores ----------------

    total_registros = len(filtrado)
    total_ids = filtrado["identificador"].nunique()
    total_locais = filtrado["localizacao"].nunique()
    total_grupos = filtrado["equipamento"].nunique()

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Registros encontrados", numero(total_registros))
    k2.metric("IDs distintos", numero(total_ids))
    k3.metric("Localizações", numero(total_locais))
    k4.metric("Grupos de equipamento", numero(total_grupos))

    st.divider()

    # ---------------- Gráfico por localização ----------------

    esquerda, direita = st.columns(2, gap="large")

    with esquerda:
        st.subheader("Onde estão os registros?")

        por_local = (
            filtrado.groupby(["localizacao", "tipo"])
            .size()
            .reset_index(name="Quantidade")
        )

        locais_top = (
            filtrado.groupby("localizacao")
            .size()
            .nlargest(15)
            .index
        )

        por_local = por_local[
            por_local["localizacao"].isin(locais_top)
        ]

        fig = px.bar(
            por_local,
            x="Quantidade",
            y="localizacao",
            color="tipo",
            barmode="stack",
            orientation="h",
            color_discrete_sequence=CORES
        )

        fig.update_layout(
            height=430,
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_title="Registros",
            yaxis_title=None,
            legend_title=None,
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------- Gráfico de funções ----------------

    with direita:
        st.subheader("Quais funções aparecem mais?")

        por_funcao = (
            filtrado.groupby("funcao")
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
            .head(12)
            .sort_values("Quantidade", ascending=True)
        )

        fig = px.bar(
            por_funcao,
            x="Quantidade",
            y="funcao",
            orientation="h",
            color="Quantidade",
            color_continuous_scale=["#B9D9EA", "#2878B5"]
        )

        fig.update_layout(
            height=430,
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_title="Registros",
            yaxis_title=None,
            coloraxis_showscale=False
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---------------- Identificadores repetidos ----------------

    st.subheader("Identificadores repetidos")

    contagem_ids = (
        filtrado.groupby("identificador")
        .agg(
            Ocorrencias=("identificador", "size"),
            Grupos=("equipamento", "nunique"),
            Localizacoes=("localizacao", "nunique"),
            Tipos=("tipo", "nunique")
        )
        .reset_index()
    )

    repetidos = contagem_ids[
        contagem_ids["Ocorrencias"] > 1
    ].sort_values("Ocorrencias", ascending=False)

    a, b = st.columns(2)

    a.metric("IDs que aparecem mais de uma vez", numero(len(repetidos)))

    if not repetidos.empty:
        b.metric(
            "Maior número de ocorrências de um ID",
            numero(int(repetidos["Ocorrencias"].max()))
        )

        st.caption(
            "Repetição não é sinônimo de erro. Um identificador pode aparecer "
            "em mais de um registro. Confira o grupo, a função e a localização."
        )

        fig = px.bar(
            repetidos.head(10).sort_values("Ocorrencias"),
            x="Ocorrencias",
            y="identificador",
            orientation="h",
            color_discrete_sequence=["#D46A6A"]
        )

        fig.update_layout(
            height=350,
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_title="Quantidade de ocorrências",
            yaxis_title=None
        )

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver detalhes dos identificadores repetidos"):
            detalhes = filtrado[
                filtrado["identificador"].isin(repetidos["identificador"])
            ].sort_values("identificador")

            st.dataframe(
                detalhes[
                    [
                        "identificador", "tipo", "equipamento",
                        "localizacao", "funcao"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )
    else:
        b.metric("Maior número de ocorrências de um ID", "1")
        st.info("Não foram encontrados identificadores repetidos neste recorte.")

    st.divider()

    # ---------------- Registros incompletos ----------------

    st.subheader("Posições sem identificador")

    # Usa as posições extraídas, incluindo aquelas cujo ID está vazio.
    # Aplica os filtros escolhidos para manter o recorte consistente.
    incompletos = dados[dados["identificador"].isna()].copy()

    incompletos = incompletos[
        incompletos["tipo"].isin(tipos_selecionados)
        & incompletos["localizacao"].isin(locais_selecionados)
        & incompletos["equipamento"].isin(equipamentos_selecionados)
        & incompletos["funcao"].isin(funcoes_selecionadas)
    ]

    c1, c2 = st.columns(2)

    c1.metric("Posições sem identificador", numero(len(incompletos)))

    total_posicoes_recorte = total_registros + len(incompletos)
    percentual_vazio = (
        len(incompletos) / total_posicoes_recorte * 100
        if total_posicoes_recorte else 0
    )

    c2.metric("Percentual vazio estimado", f"{percentual_vazio:.1f}%")

    if not incompletos.empty:
        vazios_por_local = (
            incompletos.groupby("localizacao")
            .size()
            .reset_index(name="Posições vazias")
            .sort_values("Posições vazias", ascending=False)
            .head(10)
        )

        fig = px.bar(
            vazios_por_local.sort_values("Posições vazias"),
            x="Posições vazias",
            y="localizacao",
            orientation="h",
            color_discrete_sequence=["#E5A84B"]
        )

        fig.update_layout(
            height=330,
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_title="Posições sem identificação",
            yaxis_title=None
        )

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Consultar posições sem identificador"):
            st.dataframe(
                incompletos[
                    [
                        "tipo", "equipamento", "localizacao",
                        "funcao", "linha_planilha"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.success("Não há posições vazias identificadas nesse recorte.")

    st.divider()

    # ---------------- Consulta e exportação ----------------

    with st.expander("Consultar registros detalhados"):
        st.dataframe(
            filtrado[
                [
                    "tipo", "equipamento", "localizacao",
                    "funcao", "identificador", "linha_planilha"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    csv = filtrado.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "Baixar registros filtrados em CSV",
        data=csv,
        file_name="sitcon_inventario_filtrado.csv",
        mime="text/csv"
    )

    st.divider()

    st.caption(
    "SITCON | Análise exploratória do inventário ferroviário. "
    "Os gráficos dependem dos registros extraídos das planilhas. "
    "Identificadores repetidos ou ausentes precisam ser conferidos "
    "na fonte antes de serem classificados como erros."
     )

    # Pagina 3

elif pagina == "Análise dos Sinais":

    st.title("Análise dos Sinais Luminosos")
    st.write(
        "Comparação dos grupos de sinais, quantidade de identificações "
        "e consulta dos registros cadastrados."
    )

    df_sinais = sinais.copy()

    if df_sinais.empty:
        st.warning("Nenhum registro de sinal foi encontrado.")

    else:
        preenchidos_sinais = df_sinais[
            df_sinais["identificador"].notna()
        ].copy()

        # Quantidade de identificações por grupo
        contagem = (
            preenchidos_sinais.groupby("equipamento")
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )

    
        st.subheader("Identificações por grupo de sinal")

        if contagem["equipamento"].nunique() <= 1:
            st.warning(
                "A extração encontrou apenas um grupo de sinal. "
                "Confira se os grupos SINAL 4, SINAL 6, SINAL 12 "
                "e outros foram identificados corretamente."
            )

        fig = px.bar(
            contagem.sort_values("Quantidade", ascending=True),
            x="Quantidade",
            y="equipamento",
            orientation="h",
            text="Quantidade",
            color="Quantidade",
            color_continuous_scale=["#B9D9EA", "#2878B5"],
            labels={
                "equipamento": "Grupo de sinal",
                "Quantidade": "Identificações"
            }
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            height=max(300, min(600, 45 * len(contagem) + 100)),
            template="plotly_white",
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=20, r=50, t=20, b=35),
            xaxis_title="Quantidade de identificações",
            yaxis_title=None
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )


        st.divider()

        # Ranking dos grupos
        st.subheader("Ranking dos sinais")

        esquerda, direita = st.columns(2)

        with esquerda:
            st.markdown("**Grupos com mais identificações**")
            st.dataframe(
                contagem.head(5),
                use_container_width=True,
                hide_index=True
            )

        with direita:
            st.markdown("**Grupos com menos identificações**")
            st.dataframe(
                contagem.sort_values(
                    "Quantidade", ascending=True
                ).head(5),
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # Consulta detalhada
        st.subheader("Consultar identificações")

        busca = st.text_input(
            "Pesquisar por grupo, localização ou identificador",
            placeholder="Ex.: SINAL 4, armário ou código...",
            key="busca_sinais"
        )

        tabela = df_sinais.copy()

        if busca.strip():
            mascara = tabela[
                ["equipamento", "localizacao", "identificador", "funcao"]
            ].astype(str).apply(
                lambda coluna: coluna.str.contains(
                    busca.strip(),
                    case=False,
                    na=False,
                    regex=False
                )
            ).any(axis=1)

            tabela = tabela[mascara]

        st.dataframe(
            tabela[
                [
                    "equipamento",
                    "localizacao",
                    "funcao",
                    "identificador",
                    "linha_planilha"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Os grupos são comparados usando as identificações "
            "preenchidas na planilha. Os registros vazios continuam "
            "disponíveis na tabela para consulta."
        )

# Pagina 4

elif pagina == "Análise dos CDVs":

    st.title("Análise dos Circuitos de Via (CDVs)")
    st.write(
        "Distribuição dos CDVs, funções cadastradas e associações "
        "entre circuitos e localizações."
    )

    df_cdvs = dados[
        dados["tipo"].astype(str).str.contains(
            "CDV", case=False, na=False
        )
    ].copy()

    if df_cdvs.empty:
        st.warning("Nenhum registro de CDV foi encontrado.")

    else:
        st.subheader("Registros por CDV")

        contagem_cdvs = (
            df_cdvs.groupby("equipamento")
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=True)
        )

        fig = px.bar(
            contagem_cdvs,
            x="Quantidade",
            y="equipamento",
            orientation="h",
            text="Quantidade",
            color_discrete_sequence=CORES,
            labels={
                "equipamento": "CDV",
                "Quantidade": "Registros"
            }
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            height=max(350, min(650, 40 * len(contagem_cdvs) + 100)),
            template="plotly_white",
            showlegend=False,
            margin=dict(l=20, r=45, t=20, b=35),
            xaxis_title="Quantidade de registros",
            yaxis_title=None
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

        st.divider()

        st.subheader("Funções cadastradas")

        funcoes = df_cdvs.copy()
        funcoes["funcao"] = (
            funcoes["funcao"]
            .fillna("Não preenchida")
            .replace("", "Não preenchida")
        )

        contagem_funcoes = (
            funcoes.groupby("funcao")
            .size()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )

        st.dataframe(
            contagem_funcoes,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader("Consultar registros de CDVs")

        busca_cdvs = st.text_input(
            "Pesquise por CDV, localização, função ou identificador",
            placeholder="Digite para pesquisar...",
            key="busca_cdvs"
        )

        tabela_cdvs = df_cdvs.copy()

        if busca_cdvs.strip():
            mascara = tabela_cdvs[
                [
                    "equipamento",
                    "localizacao",
                    "funcao",
                    "identificador"
                ]
            ].astype(str).apply(
                lambda coluna: coluna.str.contains(
                    busca_cdvs.strip(),
                    case=False,
                    na=False,
                    regex=False
                )
            ).any(axis=1)

            tabela_cdvs = tabela_cdvs[mascara]

        st.dataframe(
            tabela_cdvs[
                [
                    "equipamento",
                    "localizacao",
                    "funcao",
                    "identificador"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PÁGINA 5 — QUALIDADE DOS DADOS
# ============================================================

elif pagina == "Qualidade dos Dados":

    st.title("Qualidade dos Dados")
    st.write(
        "Verifique a completude do inventário, os campos ausentes "
        "e os identificadores que precisam de conferência."
    )

    total = len(dados)

    # Campos que vamos avaliar
    campos = [
        "tipo",
        "equipamento",
        "localizacao",
        "funcao",
        "identificador"
    ]

    # Considera células vazias e textos em branco
    tabela_qualidade = dados[campos].copy()

    for coluna in campos:
        tabela_qualidade[coluna] = (
            tabela_qualidade[coluna]
            .replace(r"^\s*$", pd.NA, regex=True)
        )

    ausentes = tabela_qualidade.isna().sum()
    preenchidos_total = tabela_qualidade.notna().sum().sum()
    total_celulas = tabela_qualidade.size

    percentual = (
        preenchidos_total / total_celulas * 100
        if total_celulas else 0
    )

    # Identificadores repetidos: não significa necessariamente erro
    ids = dados["identificador"].astype("string").str.strip()
    ids_validos = ids.notna() & ids.ne("")

    repetidos = ids_validos & ids.duplicated(keep=False)
    quantidade_repetidos = int(repetidos.sum())

    # Indicadores
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Registros analisados", numero(total))
    c2.metric("Completude dos campos", f"{percentual:.1f}%")
    c3.metric("Células ausentes", numero(int(ausentes.sum())))
    c4.metric("Linhas com ID repetido", numero(quantidade_repetidos))

    st.progress(percentual / 100)

    st.divider()

    # Gráfico de campos ausentes
    st.subheader("Campos com informações ausentes")

    resumo = pd.DataFrame({
        "Campo": ausentes.index,
        "Quantidade ausente": ausentes.values
    })

    resumo["Percentual ausente"] = (
        resumo["Quantidade ausente"] / total * 100
        if total else 0
    )

    resumo = resumo.sort_values(
        "Quantidade ausente",
        ascending=True
    )

    fig = px.bar(
        resumo,
        x="Quantidade ausente",
        y="Campo",
        orientation="h",
        text="Quantidade ausente",
        color="Quantidade ausente",
        color_continuous_scale=["#B9D9EA", "#2878B5"],
        labels={
            "Quantidade ausente": "Células vazias",
            "Campo": ""
        }
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=350,
        template="plotly_white",
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(l=10, r=45, t=20, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        resumo.sort_values(
            "Quantidade ausente",
            ascending=False
        ).reset_index(drop=True),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Identificadores repetidos
    st.subheader("Identificadores que aparecem mais de uma vez")

    if quantidade_repetidos > 0:
        tabela_repetidos = dados.loc[repetidos].copy()

        contagem_ids = (
            ids[repetidos]
            .value_counts()
            .rename_axis("Identificador")
            .reset_index(name="Ocorrências")
        )

        tabela_repetidos["identificador"] = (
            tabela_repetidos["identificador"].astype("string").str.strip()
        )

        tabela_repetidos = tabela_repetidos.merge(
            contagem_ids,
            left_on="identificador",
            right_on="Identificador",
            how="left"
        )

        st.caption(
            "Repetições são pontos de atenção, mas podem ser legítimas "
            "dependendo do equipamento e da organização da planilha."
        )

        st.dataframe(
            tabela_repetidos[
                [
                    "tipo",
                    "equipamento",
                    "localizacao",
                    "funcao",
                    "identificador",
                    "Ocorrências"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Nenhum identificador repetido foi encontrado.")

    st.divider()

    # Registros sem identificador
    st.subheader("Registros sem identificador")

    sem_id = tabela_qualidade["identificador"].isna()

    if sem_id.any():
        st.warning(
            f"{int(sem_id.sum())} registros estão sem identificador."
        )

        st.dataframe(
            dados.loc[sem_id, campos],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success(
            "Todos os registros extraídos possuem identificador."
        )
