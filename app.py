import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from data import carregar, carregar_brutos
from ui import brl, nome_mes

st.set_page_config(page_title="Contas de Casa", page_icon="🏠", layout="wide",
                   initial_sidebar_state="collapsed")
ui.aplicar_css()

PESSOAS = ["MIRELLA", "THALLYS"]


def tabela(df: pd.DataFrame, **kw):
    st.dataframe(df, hide_index=True, width="stretch", **kw)


def moeda(nome: str, casas: int = 0):
    # "localized" usa o separador do navegador (523,80 num celular em português)
    return st.column_config.NumberColumn(f"{nome} (R$)", format="localized", step=10 ** -casas)


df, MESADA, fonte = carregar()
hoje = pd.Timestamp.today().normalize()
mes_hoje = hoje.to_period("M")
desp = df[df["TIPO"] == "DESPESA"]
rec = df[df["TIPO"] == "RECEITA"]
meses_disp = sorted(df["mes"].unique())
realizados = [m for m in meses_disp if m <= mes_hoje]

# ---------- topo ----------
st.title("🏠 Contas de Casa")
opcoes = meses_disp[::-1]
with st.container(horizontal=True, vertical_alignment="bottom"):
    mes_ref = st.selectbox("Mês do cartão", opcoes, index=opcoes.index(mes_hoje) if mes_hoje in opcoes else 0,
                           format_func=nome_mes, width=180)
    if st.button("Atualizar", icon="🔄", help="Reler a planilha agora"):
        carregar_brutos.clear()
        st.rerun()
st.caption(f"Fonte: {fonte} · relê sozinho a cada 10 min")

aba_mes, aba_futuro, aba_hist, aba_patri = st.tabs(["Mês", "Próximos meses", "Histórico", "Patrimônio"])

# ---------- aba: mês ----------
with aba_mes:
    d_mes = desp[desp["mes"] == mes_ref]
    dias_mes = calendar.monthrange(mes_ref.year, mes_ref.month)[1]
    dias_restantes = dias_mes - hoje.day + 1 if mes_ref == mes_hoje else None

    st.subheader("Mesada")
    cartoes = []
    for p in PESSOAS:
        dp = d_mes[d_mes["PESSOA"] == p]
        cartoes.append(ui.cartao_pessoa(p, ui.PESSOA_COR[p], dp["valor"].sum(),
                                        dp.loc[dp["compromisso"], "valor"].sum(), MESADA.get(p, 0), dias_restantes))
    st.markdown(f'<div class="cards pessoas">{"".join(cartoes)}</div>', unsafe_allow_html=True)

    with st.expander("Lançamentos individuais do mês"):
        ind = d_mes[d_mes["PESSOA"].isin(PESSOAS)].sort_values(["PESSOA", "valor"], ascending=[True, False])
        tabela(ind[["PESSOA", "DESCRICAO", "CATEGORIA", "valor"]].rename(
            columns={"PESSOA": "Pessoa", "DESCRICAO": "Descrição", "CATEGORIA": "Categoria"}),
            column_config={"valor": moeda("Valor", 2)})

    st.subheader("Mês × últimos 6 meses")
    anteriores = [mes_ref - i for i in range(1, 7)]
    base = desp[desp["mes"].isin(anteriores)]
    med_total = base.groupby("mes")["valor"].sum().reindex(anteriores, fill_value=0).median()
    med_casal = (base[base["PESSOA"] == "CASAL"].groupby("mes")["valor"].sum()
                 .reindex(anteriores, fill_value=0).median())
    despesa_mes = d_mes["valor"].sum()
    casal_mes = d_mes.loc[d_mes["PESSOA"] == "CASAL", "valor"].sum()
    receita_mes = rec.loc[rec["mes"] == mes_ref, "valor"].sum()
    sobra = receita_mes - despesa_mes
    ui.cards([
        ("Despesa total", brl(despesa_mes), ui.delta_html(despesa_mes - med_total, "vs mediana")),
        ("Despesa do casal", brl(casal_mes), ui.delta_html(casal_mes - med_casal, "vs mediana")),
        ("Receita", brl(receita_mes), "lançada até agora" if mes_ref == mes_hoje else "no mês"),
        ("Sobra", brl(sobra), f"<b>{sobra / receita_mes:.0%}</b> da receita" if receita_mes else "sem receita lançada"),
    ])

    st.subheader("Casal por categoria")
    st.caption("Barra = este mês · traço = mediana dos 6 meses anteriores")
    cat_mes = d_mes[d_mes["PESSOA"] == "CASAL"].groupby("CATEGORIA")["valor"].sum()
    cat_med = (base[base["PESSOA"] == "CASAL"].pivot_table(index="mes", columns="CATEGORIA", values="valor",
                                                           aggfunc="sum")
               .reindex(anteriores).fillna(0).median())
    comp = pd.DataFrame({"mes": cat_mes, "mediana": cat_med}).fillna(0)
    comp = comp[(comp > 1).any(axis=1)].sort_values("mes")
    nomes = [c.title() for c in comp.index]
    fig = go.Figure()
    fig.add_bar(x=comp["mes"], y=nomes, orientation="h", name="Este mês", marker_color=ui.SERIE,
                marker_cornerradius=4, hovertemplate="Este mês: R$ %{x:,.0f}<extra></extra>")
    fig.add_scatter(x=comp["mediana"], y=nomes, mode="markers", name="Mediana 6m",
                    marker=dict(symbol="line-ns", size=16, line=dict(width=3, color=ui.REFERENCIA)),
                    hovertemplate="Mediana 6m: R$ %{x:,.0f}<extra></extra>")
    ui.layout(fig, altura=max(260, 30 * len(comp) + 60), moeda_y=False)
    fig.update_layout(hovermode="y unified")
    fig.update_xaxes(showgrid=True, gridcolor=ui.GRID, tickprefix="R$ ", tickformat=",.0f")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont_color=ui.INK2)
    ui.grafico(fig)

    comp["dif"] = comp["mes"] - comp["mediana"]
    acima = comp[comp["dif"] > 50].sort_values("dif", ascending=False).head(3)
    if not acima.empty:
        st.markdown('<div class="dica"><b>Mais acima do normal:</b> ' + " · ".join(
            f"{c.title()} <span class='delta-ruim'>+{brl(v)}</span>" for c, v in acima["dif"].items()) + "</div>",
            unsafe_allow_html=True)

# ---------- aba: próximos meses ----------
with aba_futuro:
    st.caption("O que já está lançado para os próximos meses: parcelas, fixos e gastos futuros.")
    futuros = [mes_ref + i for i in range(1, 13)]
    d_fut = desp[desp["mes"].isin(futuros)]
    prox = futuros[0]
    itens = []
    for p in PESSOAS:
        comp_p = d_fut.loc[(d_fut["mes"] == prox) & (d_fut["PESSOA"] == p), "valor"].sum()
        itens.append((f"{p.title()} · livre em {nome_mes(prox)}", brl(MESADA.get(p, 0) - comp_p),
                      f"<b>{brl(comp_p)}</b> já comprometidos"))
    casal_prox = d_fut.loc[(d_fut["mes"] == prox) & (d_fut["PESSOA"] == "CASAL"), "valor"].sum()
    itens.append((f"Casal · já lançado em {nome_mes(prox)}", brl(casal_prox), "fixos e parcelas"))
    ui.cards(itens)

    st.subheader("Mesada comprometida")
    eixo = [nome_mes(m) for m in futuros]
    fig = go.Figure()
    for p in PESSOAS:
        serie = d_fut[d_fut["PESSOA"] == p].groupby("mes")["valor"].sum().reindex(futuros, fill_value=0)
        fig.add_bar(x=eixo, y=serie.values, name=p.title(), marker_color=ui.PESSOA_COR[p], marker_cornerradius=4,
                    hovertemplate=f"{p.title()}: R$ %{{y:,.0f}}<extra></extra>")
    fig.add_hline(y=MESADA["MIRELLA"], line_width=1.5, line_dash="dot", line_color=ui.REFERENCIA,
                  annotation_text="mesada", annotation_position="top left", annotation_font_color=ui.INK2)
    ui.layout(fig, altura=320)
    fig.update_yaxes(tickformat=",.0f")
    ui.grafico(fig)

    st.subheader("Parcelas em aberto")
    parc = desp[desp["eh_parcela"] & (desp["mes"] >= mes_ref)].copy()
    parc["item"] = parc["DESCRICAO"].str.replace(r"\s*\d{1,2}\s*/\s*\d{1,2}\s*", " ", regex=True).str.strip()
    resumo = (parc.groupby(["PESSOA", "item"])
              .agg(parcela=("valor", "last"), restantes=("valor", "size"), falta=("valor", "sum"), ultima=("mes", "max"))
              .reset_index().sort_values("falta", ascending=False))
    resumo["ultima"] = resumo["ultima"].map(nome_mes)
    resumo["PESSOA"] = resumo["PESSOA"].str.title()
    tabela(resumo.rename(columns={"PESSOA": "Pessoa", "item": "Item", "restantes": "Restam", "ultima": "Última"}),
           column_config={"parcela": moeda("Parcela", 2), "falta": moeda("Falta pagar")})

# ---------- aba: histórico ----------
with aba_hist:
    with st.popover("Filtros", icon="🔎"):
        ini, fim = st.select_slider("Período", options=realizados,
                                    value=(realizados[max(0, len(realizados) - 12)], realizados[-1]),
                                    format_func=nome_mes)
        f_pessoa = st.multiselect("Pessoa", sorted(df["PESSOA"].unique()))
        f_cat = st.multiselect("Categoria", sorted(df["CATEGORIA"].unique()))
        f_cls = st.multiselect("Classificação", sorted(df["CLASSIFICACAO"].unique()))
    st.caption(f"{nome_mes(ini)} a {nome_mes(fim)}"
               + "".join(f" · {', '.join(s).title()}" for s in [f_pessoa, f_cat, f_cls] if s))

    h = df[(df["mes"] >= ini) & (df["mes"] <= fim)]
    for col, sel in [("PESSOA", f_pessoa), ("CATEGORIA", f_cat), ("CLASSIFICACAO", f_cls)]:
        if sel:
            h = h[h[col].isin(sel)]
    periodo = pd.period_range(ini, fim, freq="M")
    n_meses = len(periodo)
    h_desp, h_rec = h[h["TIPO"] == "DESPESA"], h[h["TIPO"] == "RECEITA"]
    tot_d, tot_r = h_desp["valor"].sum(), h_rec["valor"].sum()
    ui.cards([
        ("Despesa média/mês", brl(tot_d / n_meses), f"<b>{brl(tot_d)}</b> em {n_meses} meses"),
        ("Receita média/mês", brl(tot_r / n_meses), f"<b>{brl(tot_r)}</b> no período"),
        ("Taxa de poupança", f"{(tot_r - tot_d) / tot_r:.0%}" if tot_r else "–", "receita menos despesa"),
    ])

    st.subheader("Receita × despesa")
    eixo = [nome_mes(m) for m in periodo]
    serie_d = h_desp.groupby("mes")["valor"].sum().reindex(periodo, fill_value=0)
    serie_r = h_rec.groupby("mes")["valor"].sum().reindex(periodo, fill_value=0)
    fig = go.Figure()
    for nome, serie, cor in [("Receita", serie_r, ui.RECEITA), ("Despesa", serie_d, ui.DESPESA)]:
        if serie.sum() > 0:
            fig.add_scatter(x=eixo, y=serie.values, name=nome, mode="lines+markers", line=dict(color=cor, width=2),
                            marker=dict(size=8, color=cor, line=dict(width=2, color="#fcfcfb")),
                            hovertemplate=f"{nome}: R$ %{{y:,.0f}}<extra></extra>")
    ui.layout(fig, altura=320)
    fig.update_yaxes(tickformat=",.0f", rangemode="tozero")
    ui.grafico(fig)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Média mensal por categoria")
        cat = (h_desp.groupby("CATEGORIA")["valor"].sum() / n_meses).sort_values()
        cat = cat[cat > 1]
        fig = go.Figure(go.Bar(x=cat.values, y=[c.title() for c in cat.index], orientation="h",
                               marker_color=ui.SERIE, marker_cornerradius=4,
                               hovertemplate="%{y}: R$ %{x:,.0f}/mês<extra></extra>"))
        ui.layout(fig, altura=max(260, 24 * len(cat) + 30), legenda=False, moeda_y=False)
        fig.update_layout(hovermode="closest")
        fig.update_xaxes(showgrid=True, gridcolor=ui.GRID, tickprefix="R$ ", tickformat=",.0f")
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont_color=ui.INK2)
        ui.grafico(fig)
    with col2:
        st.subheader("Gasto individual × mesada")
        ind = (h_desp[h_desp["PESSOA"].isin(PESSOAS)].pivot_table(index="mes", columns="PESSOA", values="valor",
                                                                   aggfunc="sum")
               .reindex(periodo).fillna(0))
        fig = go.Figure()
        for p in [p for p in PESSOAS if p in ind.columns]:
            cor = ui.PESSOA_COR[p]
            fig.add_scatter(x=eixo, y=ind[p], name=p.title(), mode="lines+markers", line=dict(color=cor, width=2),
                            marker=dict(size=8, color=cor, line=dict(width=2, color="#fcfcfb")),
                            hovertemplate=f"{p.title()}: R$ %{{y:,.0f}}<extra></extra>")
        fig.add_hline(y=MESADA["MIRELLA"], line_width=1.5, line_dash="dot", line_color=ui.REFERENCIA,
                      annotation_text="mesada", annotation_position="top left", annotation_font_color=ui.INK2)
        ui.layout(fig, altura=320)
        fig.update_yaxes(tickformat=",.0f", rangemode="tozero")
        ui.grafico(fig)
        if not ind.empty:
            acima = (ind > pd.Series(MESADA)).sum()
            st.caption(" · ".join(f"{p.title()}: acima da mesada em {acima.get(p, 0)} de {n_meses} meses"
                                  for p in ind.columns))

    cls = h_desp.groupby("CLASSIFICACAO")["valor"].sum() / n_meses
    ui.cards([(k.title(), brl(v), "média por mês") for k, v in cls.sort_values(ascending=False).items()])

    with st.expander("Lançamentos do período"):
        tabela(h.sort_values("data", ascending=False)[["data", "PESSOA", "DESCRICAO", "CATEGORIA", "CLASSIFICACAO",
                                                       "TIPO", "valor"]],
               column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                              "valor": moeda("Valor", 2)})

# ---------- aba: patrimônio ----------
with aba_patri:
    inv = df[df["TIPO"] == "INVESTIMENTO"].copy()
    if inv.empty:
        st.info("Nenhum lançamento de investimento.")
    else:
        inv["conta"] = inv["CATEGORIA"].str.title() + " · " + inv["PESSOA"].str.title()
        por_mes = inv.pivot_table(index="mes", columns="conta", values="valor", aggfunc="sum")
        # conta sem saldo no mês repete o último saldo conhecido
        por_mes = por_mes.reindex(pd.period_range(por_mes.index.min(), por_mes.index.max(), freq="M")).ffill()
        total = por_mes.sum(axis=1)
        ultimo = total.index.max()
        sub = "saldo somado das contas"
        if len(total) > 1:
            sub = ui.delta_html(total.iloc[-1] - total.iloc[-2], f"vs {nome_mes(total.index[-2])}", menor_e_bom=False)
        ui.cards([(f"Patrimônio investido · {nome_mes(ultimo)}", brl(total.iloc[-1]), sub)])
        st.caption("As linhas de INVESTIMENTO são saldo do mês, não aporte. Por isso os meses não se somam.")
        if len(total) > 1:
            fig = go.Figure(go.Scatter(x=[nome_mes(m) for m in total.index], y=total.values, mode="lines+markers",
                                       line=dict(color=ui.SERIE, width=2), marker=dict(size=8, color=ui.SERIE),
                                       hovertemplate="R$ %{y:,.0f}<extra></extra>"))
            ui.layout(fig, altura=260, legenda=False)
            fig.update_yaxes(tickformat=",.0f")
            ui.grafico(fig)
        tabela(por_mes.loc[[ultimo]].T.dropna().reset_index().set_axis(["Conta", "Saldo"], axis=1)
               .sort_values("Saldo", ascending=False), column_config={"Saldo": moeda("Saldo", 2)})
