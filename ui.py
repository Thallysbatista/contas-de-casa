"""Estilo visual: paleta, CSS, cartões em HTML e o layout padrão dos gráficos."""
import html

import plotly.graph_objects as go
import streamlit as st

# Paleta validada (CVD e contraste) com o validador da skill de dataviz.
PESSOA_COR = {"MIRELLA": "#6250d6", "THALLYS": "#1baf7a"}
RECEITA, DESPESA = "#2a78d6", "#eb6834"
SERIE = "#2a78d6"          # gráficos de uma série só
REFERENCIA = "#52514e"     # mediana, mesada e outras marcas de referência
STATUS = {"ok": "#0ca30c", "atencao": "#fab219", "estourou": "#d03b3b"}

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, EIXO = "#e1e0d9", "#c3c2b7"

NOMES_MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

CSS = """
<style>
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --line:rgba(11,11,11,.10); --card:#fcfcfb;
        --good:#006300; --bad:#b42323; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
h1 { font-size: 1.6rem !important; font-weight: 650 !important; letter-spacing: -.01em; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; margin-top: .6rem !important; }
.cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin: 4px 0 8px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.card .rot { color: var(--ink2); font-size: .82rem; font-weight: 500; }
.card .val { color: var(--ink); font-size: 1.65rem; font-weight: 650; line-height: 1.2; margin-top: 2px; }
.card .sub { color: var(--muted); font-size: .8rem; margin-top: 2px; }
.card .sub b { color: var(--ink2); font-weight: 600; }
.delta-bom { color: var(--good); font-weight: 600; }
.delta-ruim { color: var(--bad); font-weight: 600; }
.pessoa .topo { display:flex; justify-content: space-between; align-items: center; }
.pessoa .nome { font-weight: 650; font-size: 1rem; display:flex; align-items:center; gap:8px; color: var(--ink); }
.pessoa .ponto { width:10px; height:10px; border-radius: 50%; display:inline-block; }
.pill { font-size: .74rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; border: 1px solid; }
.barra { display:flex; height: 10px; border-radius: 999px; overflow: hidden; background: #ecebe6; margin: 10px 0 6px; gap: 2px; }
.barra span { display:block; height: 100%; }
.legenda { display:flex; gap: 14px; flex-wrap: wrap; color: var(--ink2); font-size: .78rem; }
.legenda i { display:inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
.dica { color: var(--ink2); font-size: .82rem; margin-top: 8px; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; overflow-x: auto; }
.stTabs [data-baseweb="tab"] { padding: 6px 10px; }
@media (max-width: 640px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: .6rem; }
  h1 { font-size: 1.3rem !important; }
  .card .val { font-size: 1.4rem; }
  .cards { grid-template-columns: 1fr 1fr; gap: 8px; }
  .cards.pessoas { grid-template-columns: 1fr; }
  .card { padding: 12px; }
  .cards > .card:last-child:nth-child(odd) { grid-column: 1 / -1; }
}
</style>
"""


def aplicar_css():
    st.markdown(CSS, unsafe_allow_html=True)


def brl(v: float, casas: int = 0) -> str:
    s = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'−' if v < 0 else ''}R$ {s}"


def nome_mes(p) -> str:
    return f"{NOMES_MES[p.month - 1]}/{str(p.year)[2:]}"


def delta_html(diff: float, ref_txt: str, menor_e_bom: bool = True) -> str:
    if abs(diff) < 1:
        return f"igual {ref_txt}"
    bom = (diff < 0) == menor_e_bom
    seta = "▲" if diff > 0 else "▼"
    return f'<span class="{"delta-bom" if bom else "delta-ruim"}">{seta} {brl(abs(diff))}</span> {ref_txt}'


def cards(itens: list[tuple[str, str, str]], classe: str = ""):
    """itens: (rótulo, valor, subtítulo em HTML)."""
    corpo = "".join(
        f'<div class="card"><div class="rot">{html.escape(r)}</div><div class="val">{v}</div>'
        f'<div class="sub">{s}</div></div>' for r, v, s in itens)
    st.markdown(f'<div class="cards {classe}">{corpo}</div>', unsafe_allow_html=True)


def status_mesada(gasto: float, limite: float) -> tuple[str, str]:
    if gasto > limite:
        return "estourou", "✕ Estourou"
    if gasto > 0.85 * limite:
        return "atencao", "! Atenção"
    return "ok", "✓ No limite"


def cartao_pessoa(nome: str, cor: str, gasto: float, compromisso: float, limite: float,
                  dias_restantes: int | None) -> str:
    saldo = limite - gasto
    chave, texto = status_mesada(gasto, limite)
    cor_status = STATUS[chave]
    base = max(limite, gasto) or 1
    w_comp = 100 * compromisso / base
    w_livre = 100 * (gasto - compromisso) / base
    w_excesso = 0.0
    if gasto > limite:  # a parte que passou da mesada aparece em vermelho no fim da barra
        w_excesso = 100 * (gasto - limite) / base
        w_livre = max(0.0, w_livre - w_excesso)
    dica = ""
    if dias_restantes and saldo > 0:
        dica = f'<div class="dica">Dá <b>{brl(saldo / dias_restantes)}/dia</b> nos {dias_restantes} dias que faltam</div>'
    elif saldo < 0:
        dica = f'<div class="dica">Passou <b>{brl(-saldo)}</b> da mesada</div>'
    return f"""
<div class="card pessoa">
  <div class="topo">
    <div class="nome"><span class="ponto" style="background:{cor}"></span>{html.escape(nome.title())}</div>
    <span class="pill" style="color:{cor_status};border-color:{cor_status}">{texto}</span>
  </div>
  <div class="rot" style="margin-top:10px">{'Disponível' if saldo >= 0 else 'Acima da mesada'}</div>
  <div class="val">{brl(abs(saldo))}</div>
  <div class="sub">Gasto <b>{brl(gasto)}</b> de {brl(limite)} · {gasto / limite:.0%}</div>
  <div class="barra">
    <span style="width:{w_comp:.1f}%;background:{cor}"></span>
    <span style="width:{w_livre:.1f}%;background:{cor};opacity:.45"></span>
    <span style="width:{w_excesso:.1f}%;background:{STATUS['estourou']}"></span>
  </div>
  <div class="legenda">
    <span><i style="background:{cor}"></i>Parcelas e fixos {brl(compromisso)}</span>
    <span><i style="background:{cor};opacity:.45"></i>Outros gastos {brl(max(0, gasto - compromisso))}</span>
    {f'<span><i style="background:{STATUS["estourou"]}"></i>Acima da mesada</span>' if saldo < 0 else ''}
  </div>
  {dica}
</div>"""


def layout(fig: go.Figure, altura: int = 320, legenda: bool = True, moeda_y: bool = True) -> go.Figure:
    fig.update_layout(
        height=altura, margin=dict(l=4, r=12, t=8 if not legenda else 36, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=12, color=INK2),
        separators=",.", dragmode=False, hovermode="x unified",
        hoverlabel=dict(bgcolor="#fcfcfb", bordercolor=EIXO, font_color=INK),
        showlegend=legenda,
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font_color=INK2, title=None),
        bargap=0.3, bargroupgap=0.08,
    )
    fig.update_xaxes(showgrid=False, linecolor=EIXO, tickfont_color=MUTED, title=None, fixedrange=True,
                     tickangle=0, automargin=True)
    pontos = max((len(t.x) for t in fig.data if t.x is not None and t.orientation != "h"), default=0)
    if pontos > 7:  # no celular, um rótulo a cada dois meses
        fig.update_xaxes(dtick=2)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=EIXO, tickfont_color=MUTED, title=None,
                     fixedrange=True, tickprefix="R$ " if moeda_y else "", separatethousands=True)
    return fig


def grafico(fig: go.Figure):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})
