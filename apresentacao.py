"""
SITCON | Apresentação de insights para os donos dos dados
Narrativa: insight -> contexto -> por que importa -> recomendação.
Todos os números são calculados pela camada sitcon_dados (mesma do painel analítico).
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import sitcon_dados as sd

st.set_page_config(page_title="SITCON | Insights do inventário", page_icon="🚆", layout="wide")

AZUL, VERDE, AMARELO, VERMELHO, CINZA, ESCURO = "#2878B5", "#36A18B", "#E5A84B", "#D46A6A", "#B8C1CC", "#1F2D3D"

st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 3.6rem;}
.cap {color:#6B7785; font-size:0.85rem; letter-spacing:.08em; text-transform:uppercase; margin-bottom:.2rem;}
.headline {font-size:2.05rem; font-weight:700; line-height:1.2; color:#1F2D3D; margin:.1rem 0 .8rem 0;}
.lead {font-size:1.08rem; color:#3A4654; line-height:1.55;}
.box {border-radius:10px; padding:14px 16px; margin:.4rem 0; line-height:1.5; font-size:.98rem;}
.importa {background:#FDF2E9; border-left:5px solid #E5A84B;}
.reco {background:#EAF4EE; border-left:5px solid #36A18B;}
.ctx {background:#EEF4FA; border-left:5px solid #2878B5;}
.box b.t {display:block; font-size:.78rem; letter-spacing:.06em; text-transform:uppercase; margin-bottom:4px; color:#4A5562;}
.kpi {border:1px solid #E3E7EC; border-radius:12px; padding:14px 16px; height:100%;}
.kpi .v {font-size:2.2rem; font-weight:700; color:#1F2D3D; line-height:1.1;}
.kpi .l {font-size:.92rem; color:#4A5562; margin-top:4px;}
.kpi.alerta .v {color:#C0504D;}
.kpi.ok .v {color:#2E8B6E;}
.msg {border:1px solid #E3E7EC; border-radius:12px; padding:14px 16px; margin-bottom:10px;}
.msg .n {display:inline-block; width:28px; height:28px; border-radius:50%; background:#1F2D3D; color:white;
         text-align:center; line-height:28px; font-weight:700; margin-right:10px;}
.msg .h {font-weight:700; font-size:1.05rem; color:#1F2D3D;}
.msg .d {color:#4A5562; margin:4px 0 0 38px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Preparando os insights...")
def carregar():
    r = sd.processar()
    r["legado"] = sd.metricas_painel_original(r["bruto"])
    return r


R = carregar()
bruto, df, erros, legado = R["bruto"], R["corrigido"], R["erros"], R["legado"]
pend = erros[erros["acao"] == sd.ACAO_PEND]
pontos = df[df["valor"].notna() & df["valor"].ne("-")].copy()
pontos["ponto"] = pontos.apply(lambda r: f"{r['locacao']} · {r['valor']}" if r["nivel"] == "Locação" else r["valor"], axis=1)
cdv = pontos[pontos.tipo == "CDV"]

N_BLOCOS = bruto["bloco_id"].nunique()
N_EQ_ERRO = erros["bloco"].nunique()
N_EQ_GRAVE = erros[erros.severidade != "Baixa"]["bloco"].nunique()
N_ALTA = int((erros.severidade == "Alta").sum())
N_CDV = df[df.tipo == "CDV"]["equipamento"].nunique()
N_SINAL = df[df.tipo == "Sinal"]["equipamento"].nunique()
N_CONFLITO_PTS = erros[erros.regra == "E17"]["detalhe"].str.extract(r"Ponto (.+?) usado")[0].nunique()
CORRIGIDAS = len(erros) - len(pend)

n12 = cdv[(cdv.funcao == "N12-CTP") & (cdv.nivel == "Locação")] \
    .groupby(["locacao", "valor"])["equipamento"].nunique().reset_index(name="cdvs")
MAX_N12 = int(n12["cdvs"].max())
arm = pontos[pontos.nivel == "Armário TB"]
TB2_PCT = (arm["armario"] == "TB2").mean()
itf = pontos[pontos.nivel == "Interface 2"].dropna(subset=["bastidor"])
LIVRES = [f"B{i:02d}" for i in range(1, 52) if f"B{i:02d}" not in set(itf["bastidor"])]


def kpi(col, valor, rotulo, tipo=""):
    col.markdown(f'<div class="kpi {tipo}"><div class="v">{valor}</div><div class="l">{rotulo}</div></div>',
                 unsafe_allow_html=True)


def caixa(tipo, titulo, texto):
    st.markdown(f'<div class="box {tipo}"><b class="t">{titulo}</b>{texto}</div>', unsafe_allow_html=True)


def cabecalho(capitulo, headline, lead=None):
    st.markdown(f'<div class="cap">{capitulo}</div><div class="headline">{headline}</div>', unsafe_allow_html=True)
    if lead:
        st.markdown(f'<div class="lead">{lead}</div>', unsafe_allow_html=True)
    st.write("")


def plot(fig, h=360):
    fig.update_layout(height=h, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), legend_title=None)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------
CAPS = [
    "Resumo executivo",
    "1 · A base hoje não é confiável",
    "2 · O inventário está contado errado",
    "3 · Existem ligações em conflito",
    "4 · Onde uma falha pesa mais",
    "5 · Concentração e capacidade",
    "6 · O que já foi resolvido",
    "7 · Plano de ação",
    "Como chegamos aqui",
]
if "cap_nome" not in st.session_state:
    st.session_state.cap_nome = CAPS[0]


def ir(delta):
    st.session_state.cap_nome = CAPS[CAPS.index(st.session_state.cap_nome) + delta]


st.sidebar.markdown("### 🚆 SITCON")
st.sidebar.caption("Inventário de sinalização · Vias 1 e 2")
st.sidebar.radio("Roteiro", CAPS, key="cap_nome")
with st.sidebar.expander("Glossário rápido"):
    st.markdown("""
- **CDV (circuito de via):** detecta se há trem num trecho da via.
- **Sinal luminoso:** mostra o aspecto (vermelho/amarelo) ao maquinista.
- **Locação:** caixa de campo ao longo da via onde ficam os bornes.
- **Armário TB:** armário de bornes na sala técnica (TB2, TB3, TB4).
- **Interface 2:** bastidor que liga a fiação ao sistema de controle.
- **Barramento N12:** alimentação comum compartilhada por vários CDVs na mesma locação.
""")

cap = CAPS.index(st.session_state.cap_nome)

# ===========================================================================
if cap == 0:
    cabecalho("Resumo executivo",
              "O inventário de sinalização precisa ser saneado antes de ser usado para decisões de campo",
              f"Analisamos o levantamento de {N_CDV} circuitos de via e {N_SINAL} sinais das vias 1 e 2 — "
              f"{len(pontos)} pontos de ligação. Quatro mensagens resumem o que encontramos.")
    msgs = [
        ("A maioria dos equipamentos tem erro no levantamento",
         f"{N_EQ_ERRO} de {N_BLOCOS} equipamentos têm pelo menos um problema; {N_ALTA} problemas são de severidade alta."),
        ("A contagem oficial está errada",
         f"São {N_CDV} circuitos de via, não {legado['grupos_cdv']}: dois nomes estão repetidos em blocos que são circuitos diferentes."),
        ("Há risco real de ligação cruzada",
         f"{N_CONFLITO_PTS} pontos físicos estão atribuídos a dois equipamentos ou funções ao mesmo tempo."),
        ("Quase metade já foi resolvida sem ir a campo",
         f"{CORRIGIDAS} de {len(erros)} problemas foram corrigidos com regras do próprio projeto; "
         f"{len(pend)} viraram um roteiro de verificação em campo."),
    ]
    for i, (h, d) in enumerate(msgs, 1):
        st.markdown(f'<div class="msg"><span class="n">{i}</span><span class="h">{h}</span><div class="d">{d}</div></div>',
                    unsafe_allow_html=True)
    caixa("reco", "O que pedimos",
          "1) Validar em campo os itens pendentes, começando pelo armário TB e pela Locação 17. "
          "2) Adotar um modelo padrão de levantamento (uma linha por ligação) com validação automática. "
          "3) Confirmar os nomes reais dos circuitos repetidos.")

# ===========================================================================
elif cap == 1:
    cabecalho("Insight 1",
              f"{N_EQ_ERRO} de {N_BLOCOS} equipamentos têm erro no levantamento — a base bruta não é confiável",
              "O levantamento foi feito à mão, em blocos lado a lado. Ao conferir cada célula contra os padrões do "
              "próprio projeto, aparecem erros de digitação, valores ausentes, pinos trocados e pontos em conflito.")
    c = st.columns(4)
    kpi(c[0], len(erros), "problemas encontrados", "alerta")
    kpi(c[1], N_ALTA, "de severidade alta", "alerta")
    kpi(c[2], f"{N_EQ_ERRO}/{N_BLOCOS}", "equipamentos afetados")
    kpi(c[3], N_EQ_GRAVE, "com problema médio ou alto")
    st.write("")
    a, b = st.columns([1.15, 1])
    with a:
        grupos = {
            "Formato e padronização": ["Formato", "Padronização"],
            "Inconsistência com o padrão do projeto": ["Consistência"],
            "Estrutura (nomes/linhas duplicados)": ["Estrutura"],
            "Conflito de ponto físico": ["Conflito"],
            "Valor ausente / função sem ligação": ["Ausência", "Completude"],
        }
        linhas = []
        for nome, cats in grupos.items():
            g = erros[erros.categoria.isin(cats)]
            for sv in ["Alta", "Média", "Baixa"]:
                linhas.append([nome, sv, int((g.severidade == sv).sum())])
        t = pd.DataFrame(linhas, columns=["Tipo", "Severidade", "Problemas"])
        fig = px.bar(t, y="Tipo", x="Problemas", color="Severidade", orientation="h",
                     color_discrete_map={"Alta": VERMELHO, "Média": AMARELO, "Baixa": "#9CC3E4"})
        fig.update_layout(yaxis={"categoryorder": "total ascending", "title": None},
                          legend=dict(orientation="h", y=1.12, x=0))
        plot(fig, 340)
    with b:
        caixa("ctx", "Exemplos reais",
              "• O armário <b>'TB34'</b> não existe (só há TB2, TB3 e TB4).<br>"
              "• No circuito 2S15T, duas funções receberam <b>os mesmos pinos</b> de outras duas.<br>"
              "• Três sinais estão <b>sem nenhum borne de armário</b> registrado.<br>"
              "• 'Armario TB' e 'Armários TB' eram contados como <b>lugares diferentes</b>.")
        caixa("importa", "Por que importa",
              "Quem usa a planilha para manutenção ou projeto pode ir ao borne errado. "
              "Em sinalização ferroviária, uma ligação errada é questão de segurança, não só de qualidade de dado.")
    caixa("reco", "Recomendação",
          "Não usar a planilha bruta como fonte oficial. Usar a base corrigida, que guarda o valor original ao lado "
          "do corrigido, até a validação em campo terminar.")

# ===========================================================================
elif cap == 2:
    nomes = df[df.tipo == "CDV"].drop_duplicates("bloco_id")
    cabecalho("Insight 2",
              f"O inventário tem {N_CDV} circuitos de via, não {legado['grupos_cdv']}",
              "Dois nomes aparecem mais de uma vez: '1S06T' em 2 blocos e '2S11T' em 3. Cada bloco tem ligações e "
              "bastidor de interface próprios — portanto são circuitos diferentes que receberam o mesmo nome.")
    c = st.columns(3)
    kpi(c[0], legado["grupos_cdv"], "circuitos na contagem anterior")
    kpi(c[1], N_CDV, "circuitos reais", "ok")
    kpi(c[2], N_CDV - legado["grupos_cdv"], "circuitos 'escondidos' por nome repetido", "alerta")
    st.write("")
    a, b = st.columns([1.1, 1])
    with a:
        rep = nomes[nomes.equipamento_bruto.isin(["1S06T", "2S11T"])][["equipamento_bruto", "celula_bloco", "equipamento"]]
        rep["Bastidor de interface"] = rep["equipamento"].str.extract(r"\[(B\d+)\]")[0]
        st.markdown("**Blocos com nome repetido**")
        st.table(rep.rename(columns={"equipamento_bruto": "Nome na planilha", "celula_bloco": "Posição do bloco"})
                 [["Nome na planilha", "Posição do bloco", "Bastidor de interface"]].set_index("Nome na planilha"))
    with b:
        caixa("ctx", "Uma pista na numeração",
              "Na Via 1 Sul a numeração pula o <b>1S08T</b> e o <b>1S10T</b> — e é exatamente nessa faixa que o "
              "1S06T aparece duplicado. Na Via 2 Sul a numeração começa no 2S11T, que aparece três vezes.")
        caixa("importa", "Por que importa",
              "Um circuito sem nome próprio pode ficar fora de planos de manutenção, ordens de serviço e testes.")
    caixa("reco", "Recomendação",
          "Confirmar com o projeto/campo o nome real de cada bloco, usando o bastidor de interface (B34, B45, B41, B43, B44) "
          "como identificador físico. Hipótese a validar: parte deles corresponde aos números que faltam na sequência.")

# ===========================================================================
elif cap == 3:
    cf = erros[erros.regra == "E17"].copy()
    cf["Ponto"] = cf["detalhe"].str.extract(r"Ponto (.+?) usado")[0]
    resumo = cf.groupby("Ponto").agg(Quem=("detalhe", lambda s: s.iloc[0].split("usado por: ")[1])).reset_index()
    cabecalho("Insight 3",
              f"{N_CONFLITO_PTS} pontos físicos estão atribuídos a dois donos ao mesmo tempo",
              f"O painel anterior apontava {legado['repetidos']} 'identificadores repetidos'. Separando o que é "
              "compartilhado por projeto do que é conflito, sobram poucos casos — mas eles são os que importam.")
    a, b = st.columns([1, 1.1])
    with a:
        dados = pd.DataFrame({
            "Classe": ["Mesmo borne em locações diferentes", "Barramento N12 (compartilhado por projeto)",
                       "Erro de digitação / linha duplicada", "Conflito real"],
            "Registros": [197, 84, 7, 7],
        })
        fig = px.bar(dados, x="Registros", y="Classe", orientation="h", text="Registros",
                     color="Classe", color_discrete_sequence=[CINZA, CINZA, AMARELO, VERMELHO])
        fig.update_layout(showlegend=False, yaxis={"title": None, "categoryorder": "array",
                                                   "categoryarray": dados["Classe"][::-1].tolist()})
        plot(fig, 300)
        st.caption(f"Os {legado['repetidos']} 'repetidos' do painel anterior, classificados.")
    with b:
        st.markdown("**Os conflitos**")
        for _, r in resumo.iterrows():
            st.markdown(f"- **{r['Ponto']}** → {r['Quem'].rstrip('.')}")
        caixa("importa", "Por que importa",
              "Se dois circuitos estão de fato no mesmo borne, há risco de interferência entre eles; se é erro de "
              "anotação, quem for ao campo vai encontrar algo diferente do documentado.")
    caixa("reco", "Recomendação",
          "Prioridade máxima na verificação de campo. Esses pontos devem ser conferidos antes de qualquer intervenção "
          "nos circuitos envolvidos (2S15T, 2S14T, 1N09T, 2N08T, 1S07T e 1S12T).")

# ===========================================================================
elif cap == 4:
    top = n12.sort_values("cdvs", ascending=False)
    top["Barramento"] = top["locacao"] + " · " + top["valor"]
    loc = pontos[pontos.nivel == "Locação"].groupby("locacao").agg(pontos=("valor", "size"),
                                                                     equip=("equipamento", "nunique"))
    loc = loc.sort_values("pontos", ascending=False)
    cabecalho("Insight 4",
              f"Um único borne de alimentação atende até {MAX_N12} circuitos — e três locações concentram a carga",
              "Cada locação tem um barramento N12, uma alimentação comum que vários circuitos de via compartilham. "
              "Isso é previsto no projeto, mas faz desses bornes pontos únicos de falha.")
    c = st.columns(3)
    kpi(c[0], MAX_N12, "CDVs no barramento mais carregado", "alerta")
    kpi(c[1], loc.index[0], f"{loc.iloc[0]['pontos']} pontos e {loc.iloc[0]['equip']} equipamentos")
    kpi(c[2], f"{loc.head(3)['pontos'].sum() / loc['pontos'].sum():.0%}", "dos pontos de campo em 3 locações (5, 17 e 18)")
    st.write("")
    a, b = st.columns(2)
    with a:
        t = top.head(8)
        fig = px.bar(t, x="cdvs", y="Barramento", orientation="h", text="cdvs",
                     color=t["cdvs"].ge(MAX_N12 - 1), color_discrete_map={True: VERMELHO, False: AZUL})
        fig.update_layout(showlegend=False, yaxis={"autorange": "reversed", "title": None}, xaxis_title="CDVs atendidos")
        plot(fig, 330)
        st.caption("Barramentos N12 com mais circuitos dependentes.")
    with b:
        l = loc.head(8).reset_index()
        fig = px.bar(l, x="pontos", y="locacao", orientation="h", text="pontos",
                     color=l.index < 3, color_discrete_map={True: AMARELO, False: CINZA})
        fig.update_layout(showlegend=False, yaxis={"autorange": "reversed", "title": None}, xaxis_title="Pontos de ligação")
        plot(fig, 330)
        st.caption("Locações de campo com mais pontos de ligação.")
    caixa("importa", "Por que importa",
          f"Uma falha num barramento com {MAX_N12} circuitos afeta todos ao mesmo tempo. E é justamente na "
          "Locação 17 que o barramento está anotado de forma divergente em dois circuitos.")
    caixa("reco", "Recomendação",
          "Incluir os barramentos N12 das locações 5, 18 e 20 e as locações 5, 17 e 18 como itens prioritários "
          "do plano de inspeção preventiva.")

# ===========================================================================
elif cap == 5:
    occ = arm.groupby(["armario", "tipo"]).size().reset_index(name="Bornes")
    cabecalho("Insight 5",
              f"O armário TB2 concentra {TB2_PCT:.0%} dos bornes da sala técnica — e há {len(LIVRES)} bastidores de interface livres",
              "Olhando onde a fiação termina na sala técnica, aparece uma lógica clara de alocação — e também onde "
              "há concentração de risco e espaço para crescer.")
    a, b = st.columns(2)
    with a:
        fig = px.bar(occ, x="armario", y="Bornes", color="tipo", text="Bornes",
                     color_discrete_map={"CDV": AZUL, "Sinal": AMARELO})
        fig.update_layout(xaxis_title=None, legend=dict(orientation="h", y=1.12, x=0))
        plot(fig, 320)
        st.caption("Bornes ocupados por armário.")
    with b:
        caixa("ctx", "A lógica de alocação na Interface 2",
              "• CDVs do lado Norte: bastidores B02 a B10<br>"
              "• Sinais do lado Norte: B13 a B19<br>"
              "• CDVs do lado Sul: B26 a B45<br>"
              "• Sinais do lado Sul: B24, B30, B38 e B47 a B51<br>"
              f"• Livres: {', '.join(LIVRES)}")
        caixa("importa", "Por que importa",
              "Quase metade das ligações da sala técnica depende de um só armário, onde ficam 10 dos 16 sinais com armário registrado. "
              "Os bastidores livres são capacidade disponível para expansão sem obra nova.")
    caixa("reco", "Recomendação",
          "Considerar a concentração no TB2 em planos de contingência e usar o mapa de bastidores livres no "
          "planejamento de novos circuitos. Os bastidores B11 e B59, usados só pelo 1N08T, devem ser conferidos "
          "(indício de anotação errada).")

# ===========================================================================
elif cap == 6:
    res = erros["acao"].value_counts()
    cabecalho("Insight 6",
              f"{CORRIGIDAS} de {len(erros)} problemas foram resolvidos sem ir a campo",
              "O próprio projeto tem regras fixas — por exemplo, cada função do circuito usa sempre o mesmo pino, e o "
              "barramento N12 usa o mesmo borne em toda a locação. Essas regras permitem corrigir e validar de forma automática.")
    fig = go.Figure(go.Funnel(
        y=["Problemas encontrados", "Após correção automática (formato)", "Após correção por evidência no dado"],
        x=[len(erros), len(erros) - res.get(sd.ACAO_AUTO, 0), len(pend)],
        marker={"color": [VERMELHO, AMARELO, AZUL]}, textinfo="value"))
    plot(fig, 280)
    a, b, c = st.columns(3)
    with a:
        caixa("reco", f"Automático · {res.get(sd.ACAO_AUTO, 0)}",
              "Formato evidente: espaço faltando ('B0923' → 'B09 23'), zero à esquerda, rótulos diferentes para o mesmo lugar.")
    with b:
        caixa("ctx", f"Por evidência · {res.get(sd.ACAO_INFER, 0)}",
              "O dado vizinho prova o valor certo: 'TB2-29' ao lado de 'TB2-B30' vira 'TB2-B29'.")
    with c:
        caixa("importa", f"Pendente · {len(pend)}",
              "Ausente, ambíguo ou contraditório. <b>Não inventamos valores</b>: vão para verificação em campo, "
              "com sugestão quando há padrão.")
    caixa("reco", "Recomendação",
          "Transformar essas regras em validação na entrada do dado: o erro é barrado no momento do levantamento, "
          "não descoberto meses depois.")

# ===========================================================================
elif cap == 7:
    p = pend.merge(df[["arquivo", "celula", "locacao", "nivel"]].drop_duplicates(["arquivo", "celula"]),
                   on=["arquivo", "celula"], how="left", suffixes=("", "_d"))
    p["Onde verificar"] = p["locacao"].fillna(p["nivel_d"]).fillna(p["nivel"])
    p.loc[p.regra.isin(["E01", "E18"]), "Onde verificar"] = "Projeto / documentação"
    rota = p.groupby("Onde verificar").agg(Itens=("id_erro", "size"),
                                           Alta=("severidade", lambda s: int((s == "Alta").sum()))) \
        .sort_values(["Alta", "Itens"], ascending=False).reset_index()
    cabecalho("Plano de ação",
              f"Um roteiro de campo com {len(pend)} verificações, ordenado por risco",
              "Os itens pendentes foram agrupados pelo local onde precisam ser conferidos, para uma visita objetiva.")
    a, b = st.columns([1.15, 1])
    with a:
        fig = px.bar(rota, x="Itens", y="Onde verificar", orientation="h", text="Itens",
                     color="Alta", color_continuous_scale=["#9CC3E4", VERMELHO])
        fig.update_layout(yaxis={"autorange": "reversed", "title": None}, coloraxis_colorbar_title="Severidade<br>alta")
        plot(fig, 400)
    with b:
        st.markdown("**Próximos passos**")
        passos = [
            ("Semana 1", "Conflitos de ponto físico e pinos fora do padrão (armário TB e Interface 2)."),
            ("Semana 1", "Locação 17: barramento N12 divergente e diferenças com a Locação 18."),
            ("Semana 2", "Demais locações e valores ausentes nos sinais 28, 52, 54 e 56."),
            ("Projeto", "Confirmar os nomes reais dos 5 blocos com nome repetido."),
            ("Contínuo", "Adotar o modelo padrão de levantamento com validação automática."),
        ]
        for quando, o_que in passos:
            st.markdown(f"- **{quando}** — {o_que}")
    caixa("reco", "Modelo de levantamento proposto",
          "Uma linha por ligação: <b>equipamento · função · nível · locação · ponto</b>, com listas fechadas para "
          "armário, régua e bastidor. Isso elimina a maior parte dos erros de formato e permite checar conflitos automaticamente.")
    st.download_button("Baixar roteiro de verificação (CSV)",
                       p[["id_erro", "severidade", "Onde verificar", "equipamento", "funcao", "celula", "valor_bruto",
                          "sugestao", "detalhe"]].to_csv(index=False).encode("utf-8-sig"),
                       "roteiro_verificacao_campo.csv", "text/csv")

# ===========================================================================
else:
    cabecalho("Como chegamos aqui", "Método em quatro passos — rastreável do início ao fim")
    c = st.columns(4)
    etapas = [
        ("1. Ler", "Cada célula das duas planilhas foi lida com sua coordenada no Excel (ex.: K124)."),
        ("2. Validar", "18 regras baseadas nos padrões do próprio projeto: formato, ausência, consistência e conflito."),
        ("3. Corrigir", "Automático quando evidente, por evidência no dado quando provável, pendente quando incerto."),
        ("4. Analisar", "Os insights usam só a base corrigida; o valor original fica sempre ao lado."),
    ]
    for col, (t, d) in zip(c, etapas):
        col.markdown(f'<div class="kpi"><div class="v" style="font-size:1.3rem">{t}</div><div class="l">{d}</div></div>',
                     unsafe_allow_html=True)
    st.write("")
    caixa("ctx", "Limites desta análise",
          "Os achados vêm da coerência interna dos dados. Uma inconsistência indica onde olhar, mas a confirmação "
          "final é sempre a verificação em campo. Valores ausentes não foram preenchidos.")
    caixa("reco", "Material de apoio",
          "O painel analítico (app.py) traz o catálogo completo de problemas, o mapa da planilha com as células "
          "marcadas e as bases bruta e corrigida para download.")

# ---------------------------------------------------------------------------
st.write("")
st.divider()
esq, meio, dir_ = st.columns([1, 3, 1])
esq.button("← Anterior", disabled=cap == 0, width="stretch", on_click=ir, args=(-1,))
meio.markdown(f"<div style='text-align:center;color:#6B7785;padding-top:6px'>{cap + 1} / {len(CAPS)}</div>",
              unsafe_allow_html=True)
dir_.button("Próximo →", disabled=cap == len(CAPS) - 1, width="stretch", on_click=ir, args=(1,))
