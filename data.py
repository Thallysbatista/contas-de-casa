"""Carga e limpeza dos dados da planilha CONTAS DE CASA."""
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
MESADA_PADRAO = {"MIRELLA": 2400.0, "THALLYS": 2400.0}
CSV_LOCAL = Path(os.environ.get("CONTAS_CSV", Path(__file__).parent / "data" / "contas.csv"))
RE_PARCELA = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})")


def _usa_google() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "planilha" in st.secrets
    except Exception:
        return False


def _abrir_planilha():
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return gspread.authorize(creds).open_by_key(st.secrets["planilha"]["id"])


@st.cache_data(ttl=600, show_spinner="Lendo a planilha...")
def carregar_brutos() -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Devolve (lançamentos, limites) como texto, do Google Sheets ou do CSV local."""
    if _usa_google():
        planilha = _abrir_planilha()
        aba = st.secrets["planilha"].get("aba", "CONTAS")
        linhas = planilha.worksheet(aba).get_all_values()
        brutos = pd.DataFrame(linhas[1:], columns=linhas[0])
        try:
            lim = planilha.worksheet("LIMITES").get_all_values()
            limites = pd.DataFrame(lim[1:], columns=lim[0])
        except Exception:
            limites = None
        return brutos, limites
    return pd.read_csv(CSV_LOCAL, dtype=str, keep_default_na=False), None


def _data(txt: str):
    m = re.match(r"\s*(\d{1,2}) de (\w+)\.? de (\d{4})", txt or "")
    if not m or m[2][:3].lower() not in MESES:
        return pd.NaT
    return pd.Timestamp(int(m[3]), MESES[m[2][:3].lower()], int(m[1]))


def _valor(txt: str):
    limpo = re.sub(r"[^\d,\-]", "", txt or "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return float("nan")


def limpar(brutos: pd.DataFrame) -> pd.DataFrame:
    df = brutos.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    df = df.rename(columns={"DESCRIÇÃO": "DESCRICAO", "CLASSIFICAO": "CLASSIFICACAO",
                            "CLASSIFICAÇÃO": "CLASSIFICACAO"})
    df = df[["DATA", "PESSOA", "DESCRICAO", "CATEGORIA", "CLASSIFICACAO", "TIPO", "VALOR"]]
    for c in ["PESSOA", "CATEGORIA", "CLASSIFICACAO", "TIPO"]:
        df[c] = df[c].fillna("").str.strip().str.upper()
    df["DESCRICAO"] = df["DESCRICAO"].fillna("").str.strip()
    df["data"] = df["DATA"].map(_data)
    df["valor"] = df["VALOR"].map(_valor)
    df = df.dropna(subset=["data", "valor"])
    df = df[df["TIPO"] != ""]
    df["CLASSIFICACAO"] = df["CLASSIFICACAO"].replace("", "SEM CLASSIFICAÇÃO")
    df["CATEGORIA"] = df["CATEGORIA"].replace("", "SEM CATEGORIA")
    df["mes"] = df["data"].dt.to_period("M")

    parcela = df["DESCRICAO"].str.extract(RE_PARCELA)
    df["parcela_n"] = pd.to_numeric(parcela[0], errors="coerce")
    df["parcela_total"] = pd.to_numeric(parcela[1], errors="coerce")
    df["eh_parcela"] = df["parcela_total"].gt(1) & df["parcela_n"].le(df["parcela_total"])
    df["eh_fixo"] = df["CLASSIFICACAO"].eq("FIXO") | df["DESCRICAO"].str.contains("(fixo)", case=False, regex=False)
    df["compromisso"] = df["eh_parcela"] | df["eh_fixo"]
    return df.drop(columns=["DATA", "VALOR"]).reset_index(drop=True)


def mesadas(limites: pd.DataFrame | None) -> dict[str, float]:
    """Aba LIMITES opcional, colunas PESSOA e VALOR; sem ela vale o padrão."""
    if limites is None or limites.empty:
        return dict(MESADA_PADRAO)
    lim = limites.copy()
    lim.columns = [c.strip().upper() for c in lim.columns]
    out = dict(MESADA_PADRAO)
    for _, r in lim.iterrows():
        v = _valor(r.get("VALOR", ""))
        if r.get("PESSOA") and v == v:
            out[r["PESSOA"].strip().upper()] = v
    return out


def carregar() -> tuple[pd.DataFrame, dict[str, float], str]:
    brutos, limites = carregar_brutos()
    fonte = "Google Sheets (ao vivo)" if _usa_google() else f"CSV local ({CSV_LOCAL.name})"
    return limpar(brutos), mesadas(limites), fonte
