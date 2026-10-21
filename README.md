# 🏠 Contas de Casa

Painel das finanças da casa (Thallys e Mirella), feito em Streamlit. Substitui um dashboard do Looker Studio que
mostrava números errados e não respondia às perguntas do dia a dia: *quanto ainda posso gastar este mês?*,
*o que já está comprometido nos próximos meses?*, *este mês está normal?*

Os lançamentos continuam sendo feitos na planilha Google. O app só **lê** a planilha, ao vivo, e ninguém precisa
baixar arquivo.

## Arquitetura

```
Google Sheets ──(conta de serviço, só leitura)──▶ app Streamlit ──▶ Streamlit Community Cloud (app privado)
 aba CONTAS                                       data.py → app.py      acesso só por convite de e-mail
 aba LIMITES (opcional)
```

- **Fonte:** planilha "CONTAS DE CASA", aba `CONTAS`. Ela é lida por uma conta de serviço do Google Cloud que
  tem permissão de *Leitor* compartilhada só nessa planilha.
- **Hospedagem:** Streamlit Community Cloud. O deploy sai da branch `main` deste repositório e é automático a
  cada push.
- **Privacidade:** o repositório é público, mas tem **apenas código**. A credencial e o ID da planilha ficam nos
  *secrets* do Streamlit, e nenhum dado financeiro entra no git. O app em si é privado: só quem foi convidado
  por e-mail consegue abrir.
- **Cache:** os dados ficam em cache por 10 minutos (`st.cache_data(ttl=600)`). O botão **Atualizar** limpa o
  cache e relê a planilha na hora.

## Arquivos

| Arquivo | Papel |
|---|---|
| `app.py` | Página principal: topo (mês do cartão e botão Atualizar) e as abas **Mês**, **Próximos meses**, **Histórico** e **Patrimônio** |
| `data.py` | Carga (Google Sheets via `gspread`, ou CSV local) e limpeza: datas em pt-BR, valores em R$, detecção de parcelas e fixos, mesadas |
| `ui.py` | Visual: paleta, CSS responsivo, cartões em HTML, `layout()` padrão dos gráficos Plotly, formatação `brl()` |
| `.streamlit/config.toml` | Tema claro fixo e toolbar mínima |
| `.streamlit/secrets.toml` | **Só local, fora do git.** Credencial e ID da planilha |
| `data/contas.csv` | **Só local, fora do git.** CSV exportado, usado quando não há secrets |

## A planilha

Colunas da aba `CONTAS`: `DATA, PESSOA, DESCRIÇÃO, CATEGORIA, CLASSIFICAO, TIPO, VALOR` (o nome
`CLASSIFICAO` é sem o Ç mesmo, como está na planilha).

- `DATA`: texto do tipo `1 de jul. de 2023`.
- `PESSOA`: `THALLYS`, `MIRELLA` ou `CASAL`.
- `TIPO`: `DESPESA`, `RECEITA` ou `INVESTIMENTO`.
- `CLASSIFICAO`: `FIXO`, `VARIÁVEL` ou vazio. Quando está vazio, o app mostra "SEM CLASSIFICAÇÃO".
- `VALOR`: texto do tipo ` R$  460,42 `.

Aba opcional `LIMITES`, com as colunas `PESSOA` e `VALOR`, para mudar a mesada sem mexer no código. Se não
existir, vale `MESADA_PADRAO` em `data.py`.

## Regras de negócio

- **Mês = mês do cartão.** Compras no cartão entram com a data da fatura (geralmente no dia 1). Pix e débito
  entram na data em que o dinheiro saiu da conta. Por isso o mês da coluna `DATA` já é o mês de fechamento, e o
  app não aplica nenhuma regra extra.
- **Mesada individual:** limite **total** por pessoa e por mês, sem divisão por categoria. O que conta são as
  despesas com `PESSOA` = a pessoa.
- **Parcelas contam na mesada** do mês em que caem.
- **O casal não tem teto.** As despesas do casal são só acompanhadas, comparando com a mediana dos 6 meses
  anteriores.
- **Compromisso** é um lançamento com `n/m` na descrição (parcela) ou marcado como fixo (`FIXO` ou "(fixo)" na
  descrição).
- **Lançamentos futuros** (parcelas e fixos já lançados até meses à frente) alimentam a aba *Próximos meses*. O
  Histórico só vai até o mês atual.
- **As linhas de INVESTIMENTO são saldo do mês, não aporte.** Nunca some entre meses. O patrimônio é a soma do
  último saldo conhecido de cada conta (categoria + pessoa), e uma conta sem lançamento no mês repete o saldo
  anterior.
- **Status da mesada:** ✓ *No limite* até 85% · ! *Atenção* acima de 85% · ✕ *Estourou* acima de 100%.

### Erros do Looker antigo que este app corrige
- A "média mensal" dividia o total por 12, porque agrupava pelo nome do mês e misturava os anos.
- O "investimento acumulado" somava os saldos de vários meses, contando o patrimônio várias vezes.
- O gráfico por mês juntava anos diferentes e somava investimento como se fosse gasto.

## Rodar localmente

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt    # Windows (no Linux/Mac: .venv/bin/python)
.venv/Scripts/python -m streamlit run app.py
```

Sem `.streamlit/secrets.toml`, o app lê `data/contas.csv` (ou o caminho na variável de ambiente `CONTAS_CSV`). A
barra do topo mostra a fonte em uso: "Google Sheets (ao vivo)" ou "CSV local".

Formato do `secrets.toml`, com o mesmo conteúdo colado nos *secrets* do Streamlit Cloud:

```toml
[planilha]
id = "<ID da planilha: o trecho da URL entre /d/ e /edit>"
aba = "CONTAS"

[gcp_service_account]
# todos os campos do JSON da chave da conta de serviço, um por linha
type = "service_account"
project_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
# ...
```

## Publicar mudanças

1. Altere e teste localmente.
2. Faça o commit **adicionando arquivo por arquivo** (`git add app.py ui.py ...`).
3. `git push origin main`. O Streamlit Cloud atualiza em cerca de 1 minuto.

> **Nota para o Claude:** nesta máquina, os hooks da Konsi bloqueiam `git add .`, push direto na `main` e
> `gh pr create` feitos pelo agente. Esses hooks valem para todos os repositórios, inclusive este, que é pessoal.
> O fluxo combinado é: o Claude faz e testa a mudança e o commit local, e o Thallys roda
> `! git -C C:/Users/thall/contas-de-casa push origin main`. Não contorne os hooks.

Python **3.12** no Streamlit Cloud. O pandas 3 exige Python 3.11 ou superior.

## Decisões de design

- **Paleta** (em `ui.py`), validada para daltonismo e contraste com o validador da skill de dataviz:
  - Mirella `#6250d6` (violeta) · Thallys `#1baf7a` (verde-água): **cor fixa por pessoa no app inteiro**.
  - Receita `#2a78d6` (azul) · Despesa `#eb6834` (laranja). Gráficos de uma série só usam azul.
  - Marcas de referência (mediana, mesada) em cinza `#52514e`. As cores de status (ok, atenção, estourou)
    aparecem sempre com ícone e texto, nunca só pela cor.
- **Tema claro fixo.** Um modo escuro exigiria escolher e validar outra paleta para o fundo escuro.
- **Celular primeiro:**
  - Os cartões usam CSS grid com quebra em 640px.
  - O topo usa `st.container(horizontal=True)`, que não empilha como `st.columns`.
  - Os gráficos não têm zoom nem arraste (`dragmode=False`, `fixedrange`) e mostram um rótulo de mês a cada dois
    quando há mais de 7 pontos.
  - Os filtros do Histórico ficam num `st.popover`.
- Nada de eixo duplo. Uma linha de referência tracejada marca a mesada.

## Armadilhas conhecidas

- **`$` no `st.markdown` vira LaTeX.** Um texto com dois "R$" é renderizado como fórmula. Coloque o HTML dentro
  de uma `<div>`, como fazem os cartões em `ui.py`, ou escape o `$`.
- **O servidor local não recarrega `ui.py` e `data.py` sozinho:** mudanças em módulos importados às vezes não
  aparecem. Reinicie o `streamlit run`.
- **Formatação de colunas de tabela:** `NumberColumn(format="R$ %.2f")` sai com ponto decimal. Use
  `format="localized"`, que segue o idioma do navegador, com "(R$)" no título da coluna.
- **Testes:** `streamlit.testing.v1.AppTest` para um teste rápido sem navegador. Para conferir o visual, use
  Playwright com `channel="msedge"`, viewports 1280px e 390px e `screenshot(timeout=90000)`, porque páginas
  longas demoram para capturar. O Playwright é só uma ferramenta de desenvolvimento e não fica no
  `requirements.txt`.
- **Hibernação:** o app gratuito "dorme" depois de um período sem acesso e leva uns 30 segundos para acordar.

## Ideias futuras

- Modo escuro com paleta própria.
- Alerta de ritmo: projetar o fechamento do mês pela média diária dos gastos variáveis.
- Lista de assinaturas e fixos recorrentes para revisão.
- Normalizar descrições de receita ("Salário", "salario", "SALARIO").
- Reduzir as linhas sem `CLASSIFICAO` na planilha (~40% hoje).
