import calendar

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import carregar, carregar_brutos

st.set_page_config(page_title="Contas de Casa", page_icon="🏠", layout="wide")

PESSOAS = ["MIRELLA", "THALLYS"]
CORES = {"MIRELLA": "#c2185b", "THALLYS": "#1565c0", "CASAL": "#2e7d32"}
NOMES_MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def brl(v: float, casas: int = 0) -> str:
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def nome_mes(p: pd.Period) -> str:
    return f"{NOMES_MES[p.month - 1]}/{str(p.year)[2:]}"


def tabela(df: pd.DataFrame, **kw):
    st.dataframe(df, hide_index=True, width="stretch", **kw)


df, MESADA, fonte = carregar()
hoje = pd.Timestamp.today().normalize()
mes_hoje = hoje.to_period("M")
desp = df[df["TIPO"] == "DESPESA"]
rec = df[df["TIPO"] == "RECEITA"]

# ---------- barra lateral ----------
with st.sidebar:
    st.title("🏠 Contas de Casa")
    meses_disp = sorted(df["mes"].unique())
    mes_ref = st.selectbox("Mês do cartão", meses_disp[::-1],
                           index=meses_disp[::-1].index(mes_hoje) if mes_hoje in meses_disp else 0,
                           format_func=nome_mes)
    st.caption(f"Fonte: {fonte}")
    if st.button("🔄 Atualizar dados"):
        carregar_brutos.clear()
        st.rerun()

    st.divider()
    st.subheader("Filtros do histórico")
    realizados = [m for m in meses_disp if m <= mes_hoje]
    ini, fim = st.select_slider("Período", options=realizados,
                                value=(realizados[max(0, len(realizados) - 12)], realizados[-1]),
                                format_func=nome_mes)
    f_pessoa = st.multiselect("Pessoa", sorted(df["PESSOA"].unique()))
    f_tipo = st.multiselect("Tipo", sorted(df["TIPO"].unique()), default=["DESPESA"])
    f_cat = st.multiselect("Categoria", sorted(df["CATEGORIA"].unique()))
    f_cls = st.multiselect("Classificação", sorted(df["CLASSIFICACAO"].unique()))

st.title(f"Contas de Casa · {nome_mes(mes_ref)}")
aba_mes, aba_futuro, aba_hist, aba_patri = st.tabs(
    ["📅 Mês", "🔮 Próximos meses", "📈 Histórico", "💰 Patrimônio"])

# ---------- aba: mês ----------
with aba_mes:
    d_mes = desp[desp["mes"] == mes_ref]
    receita_mes = rec.loc[rec["mes"] == mes_ref, "valor"].sum()
    despesa_mes = d_mes["valor"].sum()
    dias_mes = calendar.monthrange(mes_ref.year, mes_ref.month)[1]
    dias_restantes = dias_mes - hoje.day + 1 if mes_ref == mes_hoje else None

    st.subheader("Mesada individual")
    cols = st.columns(len(PESSOAS))
    for col, p in zip(cols, PESSOAS):
        dp = d_mes[d_mes["PESSOA"] == p]
        gasto, limite = dp["valor"].sum(), MESADA.get(p, 0)
        compromisso = dp.loc[dp["compromisso"], "valor"].sum()
        saldo = limite - gasto
        with col, st.container(border=True):
            st.markdown(f"### {p.title()}")
            a, b = st.columns(2)
            a.metric("Gasto no mês", brl(gasto), f"{gasto / limite:.0%} da mesada" if limite else None,
                     delta_color="off")
            b.metric("Saldo", brl(saldo), "estourou" if saldo < 0 else "disponível",
                     delta_color="inverse" if saldo < 0 else "normal")
            st.progress(min(gasto / limite, 1.0) if limite else 0.0)
            texto = f"Parcelas e fixos: **{brl(compromisso)}** · Livre: **{brl(gasto - compromisso)}**"
            if dias_restantes and saldo > 0:
                texto += f"  \nDá **{brl(saldo / dias_restantes)}/dia** nos {dias_restantes} dias restantes"
            st.markdown(texto)
            with st.expander("Lançamentos"):
                tabela(dp.sort_values("valor", ascending=False)[["data", "DESCRICAO", "CATEGORIA", "valor"]],
                       column_config={"data": st.column_config.DateColumn("Data", format="DD/MM"),
                                      "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})

    st.subheader("Visão geral do mês")
    anteriores = [mes_ref - i for i in range(1, 7)]
    base = desp[desp["mes"].isin(anteriores)]
    tot_ant = base.groupby("mes")["valor"].sum().reindex(anteriores, fill_value=0)
    casal_mes = d_mes.loc[d_mes["PESSOA"] == "CASAL", "valor"].sum()
    casal_ant = base[base["PESSOA"] == "CASAL"].groupby("mes")["valor"].sum().reindex(anteriores, fill_value=0)
    a, b, c, d = st.columns(4)
    a.metric("Despesa total", brl(despesa_mes), f"{despesa_mes - tot_ant.median():+,.0f} vs mediana 6m".replace(",", "."),
             delta_color="inverse")
    b.metric("Despesa do casal", brl(casal_mes), f"{casal_mes - casal_ant.median():+,.0f} vs mediana 6m".replace(",", "."),
             delta_color="inverse")
    a.caption("")
    c.metric("Receita", brl(receita_mes))
    d.metric("Sobra do mês", brl(receita_mes - despesa_mes),
             f"{(receita_mes - despesa_mes) / receita_mes:.0%} da receita" if receita_mes else "sem receita lançada",
             delta_color="off")

    st.markdown("**Casal: categorias no mês × mediana dos 6 meses anteriores**")
    cat_mes = d_mes[d_mes["PESSOA"] == "CASAL"].groupby("CATEGORIA")["valor"].sum()
    cat_med = (base[base["PESSOA"] == "CASAL"].pivot_table(index="mes", columns="CATEGORIA", values="valor", aggfunc="sum")
               .reindex(anteriores).fillna(0).median())
    comp = pd.DataFrame({"Este mês": cat_mes, "Mediana 6m": cat_med}).fillna(0)
    comp = comp[(comp > 0).any(axis=1)]
    comp["Diferença"] = comp["Este mês"] - comp["Mediana 6m"]
    comp = comp.sort_values("Mediana 6m", ascending=False)
    fig = go.Figure([go.Bar(name="Mediana 6m", x=comp.index, y=comp["Mediana 6m"], marker_color="#b0bec5"),
                     go.Bar(name="Este mês", x=comp.index, y=comp["Este mês"], marker_color=CORES["CASAL"])])
    fig.update_layout(barmode="group", height=380, margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1),
                      yaxis_tickprefix="R$ ")
    st.plotly_chart(fig, width="stretch")
    tabela(comp.reset_index(names="Categoria").sort_values("Diferença", ascending=False),
           column_config={k: st.column_config.NumberColumn(k, format="R$ %.0f")
                          for k in ["Este mês", "Mediana 6m", "Diferença"]})

# ---------- aba: próximos meses ----------
with aba_futuro:
    st.caption("O que já está lançado na planilha para os próximos meses: parcelas, fixos e qualquer gasto futuro.")
    futuros = [mes_ref + i for i in range(1, 13)]
    d_fut = desp[desp["mes"].isin(futuros)]
    linhas = []
    for m in futuros:
        dm = d_fut[d_fut["mes"] == m]
        linha = {"Mês": nome_mes(m)}
        for p in PESSOAS:
            comprometido = dm.loc[dm["PESSOA"] == p, "valor"].sum()
            linha[f"{p.title()} · comprometido"] = comprometido
            linha[f"{p.title()} · livre"] = MESADA.get(p, 0) - comprometido
        linha["Casal · comprometido"] = dm.loc[dm["PESSOA"] == "CASAL", "valor"].sum()
        linhas.append(linha)
    fut = pd.DataFrame(linhas)

    fig = go.Figure()
    for p in PESSOAS:
        fig.add_bar(name=p.title(), x=fut["Mês"], y=fut[f"{p.title()} · comprometido"], marker_color=CORES[p])
    fig.add_hline(y=MESADA["MIRELLA"], line_dash="dot", annotation_text="mesada")
    fig.update_layout(barmode="group", height=340, margin=dict(t=30, b=10), yaxis_tickprefix="R$ ",
                      title="Mesada já comprometida por mês", legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig, width="stretch")
    tabela(fut, column_config={c: st.column_config.NumberColumn(c, format="R$ %.0f") for c in fut.columns if c != "Mês"})

    st.markdown("**Parcelas em aberto**")
    parc = desp[desp["eh_parcela"] & (desp["mes"] >= mes_ref)].copy()
    parc["item"] = parc["DESCRICAO"].str.replace(r"\s*\d{1,2}\s*/\s*\d{1,2}\s*", " ", regex=True).str.strip()
    resumo = (parc.groupby(["PESSOA", "item"])
              .agg(valor_mes=("valor", "last"), restantes=("valor", "size"), total_restante=("valor", "sum"),
                   termina=("mes", "max"))
              .reset_index().sort_values("total_restante", ascending=False))
    resumo["termina"] = resumo["termina"].map(nome_mes)
    tabela(resumo.rename(columns={"PESSOA": "Pessoa", "item": "Item", "valor_mes": "Parcela",
                                  "restantes": "Restantes", "total_restante": "Falta pagar", "termina": "Última"}),
           column_config={k: st.column_config.NumberColumn(k, format="R$ %.2f") for k in ["Parcela", "Falta pagar"]})

# ---------- aba: histórico ----------
with aba_hist:
    h = df[(df["mes"] >= ini) & (df["mes"] <= fim)]
    for col, sel in [("PESSOA", f_pessoa), ("TIPO", f_tipo), ("CATEGORIA", f_cat), ("CLASSIFICACAO", f_cls)]:
        if sel:
            h = h[h[col].isin(sel)]
    n_meses = (fim - ini).n + 1
    h_desp = h[h["TIPO"] == "DESPESA"]

    a, b, c = st.columns(3)
    a.metric("Total no período", brl(h["valor"].sum()))
    b.metric("Média mensal", brl(h["valor"].sum() / n_meses))
    c.metric("Meses", n_meses)

    por_mes = h.pivot_table(index="mes", columns="TIPO", values="valor", aggfunc="sum").fillna(0)
    por_mes = por_mes.reindex(pd.period_range(ini, fim, freq="M"), fill_value=0)
    fig = go.Figure()
    for t, cor in [("RECEITA", "#2e7d32"), ("DESPESA", "#c62828"), ("INVESTIMENTO", "#6a1b9a")]:
        if t in por_mes:
            fig.add_bar(name=t.title(), x=[nome_mes(m) for m in por_mes.index], y=por_mes[t], marker_color=cor)
    fig.update_layout(barmode="group", height=360, margin=dict(t=30, b=10), yaxis_tickprefix="R$ ",
                      title="Por mês", legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig, width="stretch")

    # taxa de poupança ignora filtros de categoria, para fazer sentido
    pp = df[(df["mes"] >= ini) & (df["mes"] <= fim)].pivot_table(index="mes", columns="TIPO", values="valor",
                                                                    aggfunc="sum").fillna(0)
    if {"RECEITA", "DESPESA"} <= set(pp.columns):
        taxa = ((pp["RECEITA"] - pp["DESPESA"]) / pp["RECEITA"]).where(pp["RECEITA"] > 0)
        fig = px.line(x=[nome_mes(m) for m in taxa.index], y=taxa, markers=True,
                      title="Taxa de poupança (receita − despesa) / receita · todas as pessoas")
        fig.update_layout(height=280, margin=dict(t=40, b=10), yaxis_tickformat=".0%", xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        cat = (h_desp.groupby("CATEGORIA")["valor"].sum() / n_meses).sort_values()
        fig = px.bar(x=cat.values, y=cat.index, orientation="h", title="Média mensal por categoria")
        fig.update_layout(height=max(300, 22 * len(cat)), margin=dict(t=40, b=10), xaxis_tickprefix="R$ ",
                          xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
    with col2:
        ind = (h_desp[h_desp["PESSOA"].isin(PESSOAS)].pivot_table(index="mes", columns="PESSOA", values="valor",
                                                                   aggfunc="sum")
               .reindex(pd.period_range(ini, fim, freq="M")).fillna(0))
        fig = go.Figure()
        for p in ind.columns:
            fig.add_scatter(name=p.title(), x=[nome_mes(m) for m in ind.index], y=ind[p], mode="lines+markers",
                            line_color=CORES.get(p))
        fig.add_hline(y=MESADA["MIRELLA"], line_dash="dot", annotation_text="mesada")
        fig.update_layout(title="Gasto individual × mesada", height=380, margin=dict(t=40, b=10),
                          yaxis_tickprefix="R$ ", legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width="stretch")
        if not ind.empty:
            estouros = (ind > pd.Series(MESADA)).sum()
            st.caption(" · ".join(f"{p.title()}: acima da mesada em {estouros.get(p, 0)} de {len(ind)} meses"
                                  for p in ind.columns))

    cls = h_desp.groupby("CLASSIFICACAO")["valor"].sum() / n_meses
    st.markdown("**Média mensal por classificação:** " + " · ".join(f"{k.title()}: {brl(v)}" for k, v in cls.items()))

    with st.expander("Lançamentos do período"):
        tabela(h.sort_values("data", ascending=False)[["data", "PESSOA", "DESCRICAO", "CATEGORIA", "CLASSIFICACAO",
                                                       "TIPO", "valor"]],
               column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                              "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})

# ---------- aba: patrimônio ----------
with aba_patri:
    st.caption("As linhas de INVESTIMENTO são saldo do mês, não aporte. Por isso não se somam entre meses.")
    inv = df[df["TIPO"] == "INVESTIMENTO"].copy()
    if inv.empty:
        st.info("Nenhum lançamento de investimento.")
    else:
        inv["conta"] = inv["CATEGORIA"].str.title() + " · " + inv["PESSOA"].str.title()
        por_mes = inv.pivot_table(index="mes", columns="conta", values="valor", aggfunc="sum")
        # conta sem saldo no mês repete o último saldo conhecido
        por_mes = por_mes.reindex(pd.period_range(por_mes.index.min(), por_mes.index.max(), freq="M")).ffill()
        ultimo = por_mes.index.max()
        total = por_mes.loc[ultimo].sum()
        st.metric(f"Patrimônio investido ({nome_mes(ultimo)})", brl(total))
        fig = px.bar(por_mes.fillna(0).set_axis([nome_mes(m) for m in por_mes.index]), barmode="stack")
        fig.update_layout(height=360, margin=dict(t=10, b=10), yaxis_tickprefix="R$ ", xaxis_title=None,
                          yaxis_title=None, legend_title=None)
        st.plotly_chart(fig, width="stretch")
        tabela(por_mes.loc[[ultimo]].T.dropna().reset_index().set_axis(["Conta", "Saldo"], axis=1),
               column_config={"Saldo": st.column_config.NumberColumn("Saldo", format="R$ %.2f")})
