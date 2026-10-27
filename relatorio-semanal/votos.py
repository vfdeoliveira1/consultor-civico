#!/usr/bin/env python3
"""Monta o HTML do PDF "Votos da semana": o voto de cada deputado e senador
em todas as votações nominais da semana, em ordem alfabética, para consultar
com a busca do leitor de PDF.

Uso:
    python3 votos.py --coletados coletados.json --saida votos.html
    node pdf.js votos.html votos.pdf

Sai com código 3, sem gerar arquivo, quando a semana não teve votação nominal.
"""
import argparse
import datetime as dt
import html
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coleta import orientacao_de  # noqa: E402

COLUNAS_POR_TABELA = 8

# Forma curta de cada tipo de voto, para caber na coluna; a legenda traz a forma completa.
CURTO = {
    "Sim": "Sim", "Não": "Não", "Abstenção": "Abst.", "Obstrução": "Obstr.", "Artigo 17": "Art. 17",
    "Presidente (art. 51 RISF)": "Pres.", "Presente – Não registrou voto": "P-NRV", "Não Compareceu": "N/C",
    "Licença saúde": "Lic.", "Atividade parlamentar": "Ativ.", "Missão": "Missão",
}


def esc(t):
    return html.escape(str(t if t is not None else ""))


def chave_ordem(nome):
    s = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode().lower()
    return s


def data_br(iso):
    return dt.date.fromisoformat(iso[:10]).strftime("%d/%m") if iso else ""


def curto(voto, usados):
    if not voto:
        return "—"
    c = CURTO.get(voto, voto if len(voto) <= 7 else voto[:6] + ".")
    if c not in ("Sim", "Não"):
        usados[c] = voto
    return c


def montar_casa(nome_casa, prefixo, votacoes, cadastro, com_orientacao):
    """Devolve (legenda, tabelas, quantidade de parlamentares) de uma Casa."""
    if not votacoes:
        return "", "", 0
    codigos = [f"{prefixo}{i + 1}" for i in range(len(votacoes))]
    linhas_leg = []
    for cod, v in zip(codigos, votacoes):
        if nome_casa == "Câmara":
            sigla, url = v["proposicao"]["sigla"], v["proposicao"]["url"]
            resultado = "Aprovada" if v.get("aprovacao") == 1 else "Rejeitada" if v.get("aprovacao") == 0 else "—"
        else:
            sigla, url, resultado = v.get("materia"), v.get("url"), v.get("resultado") or "—"
        p = v.get("placar") or {}
        linhas_leg.append(
            f'<tr><td class="cod">{cod}</td><td class="num">{data_br(v.get("data"))}</td>'
            f'<td><a href="{esc(url)}">{esc(sigla)}</a><div class="nota">{esc(v.get("descricao"))}</div></td>'
            f'<td>{esc(resultado)}</td><td class="num">{p.get("sim", 0)} × {p.get("nao", 0)}</td></tr>'
        )
    legenda = (
        f'<table class="legenda"><thead><tr><th>Col.</th><th>Data</th><th>Votação</th><th>Resultado</th><th>Sim × Não</th></tr></thead>'
        f'<tbody>{"".join(linhas_leg)}</tbody></table>'
    )

    votos_por = {}
    for i, v in enumerate(votacoes):
        for pid, voto in v.get("votos") or []:
            votos_por.setdefault(pid, {})[i] = voto
    pessoas = sorted(votos_por, key=lambda pid: chave_ordem((cadastro.get(pid) or ["?"])[0]))
    usados = {}
    tabelas = []
    for ini in range(0, len(votacoes), COLUNAS_POR_TABELA):
        idx = list(range(ini, min(ini + COLUNAS_POR_TABELA, len(votacoes))))
        cab = "".join(f'<th class="voto">{codigos[i]}</th>' for i in idx)
        corpo, letra = [], None
        for pid in pessoas:
            nome, partido, uf = (cadastro.get(pid) or ["?", "", ""])[:3]
            inicial = chave_ordem(nome)[:1].upper()
            ancora = ""
            if inicial != letra and ini == 0:
                letra = inicial
                ancora = f' id="{prefixo}-{letra}"'
            celulas = []
            for i in idx:
                voto = votos_por[pid].get(i)
                o = orientacao_de(votacoes[i].get("orientacoes") or {}, partido) if com_orientacao else None
                contra = o in ("Sim", "Não") and voto in ("Sim", "Não") and voto != o
                classe = "sim" if voto == "Sim" else "nao" if voto == "Não" else "outro"
                celulas.append(f'<td class="voto {classe}{" contra" if contra else ""}">{esc(curto(voto, usados))}{"*" if contra else ""}</td>')
            corpo.append(f'<tr{ancora}><td class="nome">{esc(nome)}</td><td class="partido">{esc(partido)}-{esc(uf)}</td>{"".join(celulas)}</tr>')
        titulo = "" if len(votacoes) <= COLUNAS_POR_TABELA else f'<p class="nota">Colunas {codigos[idx[0]]} a {codigos[idx[-1]]}</p>'
        tabelas.append(f'{titulo}<table class="votos"><thead><tr><th>Nome</th><th>Partido-UF</th>{cab}</tr></thead><tbody>{"".join(corpo)}</tbody></table>')

    letras = sorted({chave_ordem((cadastro.get(pid) or ["?"])[0])[:1].upper() for pid in pessoas})
    indice = " ".join(f'<a href="#{prefixo}-{l}">{l}</a>' for l in letras)
    siglas = "; ".join(f"{c} = {esc(l)}" for c, l in sorted(usados.items()))
    tabela_html = (
        f'<p class="indice">Ir para a letra: {indice}</p>'
        + "".join(tabelas)
        + (f'<p class="nota">Outros registros: {siglas}. "—" = não consta voto nesta votação.</p>' if siglas else '<p class="nota">"—" = não consta voto nesta votação.</p>')
    )
    return legenda, tabela_html, len(pessoas)


ESTILO = """
:root { --tinta: #17211f; --tinta-2: #4b5855; --linha: #d9dedb; --acento: #0e6655; --bom: #1f7a3d; --atencao: #a3461c; --suave: #f2f5f3;
  --f-titulo: "Archivo", "Arial Narrow", Arial, sans-serif; --f-texto: "Source Serif 4", Georgia, serif; --f-dado: "IBM Plex Mono", ui-monospace, Menlo, monospace; }
body { background: #fff; color: var(--tinta); font-family: var(--f-texto); font-size: 9.5pt; line-height: 1.35; margin: 0;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1, h2 { font-family: var(--f-titulo); margin: 0; line-height: 1.15; text-wrap: balance; }
h1 { font-size: 22pt; font-weight: 800; font-stretch: 80%; }
h2 { font-size: 14pt; font-weight: 700; font-stretch: 88%; border-bottom: 1px solid var(--linha); padding-bottom: 4px; }
section { display: flex; flex-direction: column; gap: 10px; margin-top: 18px; }
.cabecalho { border-bottom: 3px double var(--tinta); padding-bottom: 10px; display: flex; flex-direction: column; gap: 6px; }
.nota { color: var(--tinta-2); font-size: 8pt; }
a { color: var(--acento); }
table { border-collapse: collapse; width: 100%; }
th, td { border-bottom: 1px solid var(--linha); padding: 2px 5px; text-align: left; vertical-align: top; }
th { font-family: var(--f-titulo); font-size: 7.5pt; letter-spacing: .05em; text-transform: uppercase; color: var(--tinta-2); }
thead { display: table-header-group; }
tr { break-inside: avoid; }
.legenda td { padding: 4px 5px; }
.cod, .voto, .num, .partido { font-family: var(--f-dado); font-variant-numeric: tabular-nums; white-space: nowrap; }
.cod { font-weight: 600; color: var(--acento); }
.voto { text-align: center; font-size: 8pt; }
.votos tbody tr:nth-child(even) { background: var(--suave); }
.nome { font-weight: 600; }
.partido { font-size: 8pt; color: var(--tinta-2); }
.sim { color: var(--bom); } .nao { color: var(--atencao); } .outro { color: var(--tinta-2); }
.contra { font-weight: 700; text-decoration: underline; }
.indice a { font-family: var(--f-dado); margin-right: 5px; }
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coletados", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--titulo-extra", default="", help='texto acrescentado ao título, ex.: "(edição de teste)"')
    a = ap.parse_args()
    k = json.load(open(a.coletados, encoding="utf-8"))
    cam = [v for v in (k.get("camara") or {}).get("votacoes", []) if v.get("votos") and v.get("proposicao")]
    sen = [v for v in (k.get("senado") or {}).get("votacoes", []) if v.get("votos")]
    if not cam and not sen:
        print("Semana sem votação nominal: o PDF de votos não é gerado.")
        sys.exit(3)

    ini, fim = k["semana"]["inicio"], k["semana"]["fim"]
    periodo = f"{data_br(ini)} a {dt.date.fromisoformat(fim).strftime('%d/%m/%Y')}"
    titulo = f"Votos da semana {periodo} {a.titulo_extra}".strip()
    partes = []
    for nome_casa, prefixo, lista, cadastro, quem in (
        ("Câmara", "C", cam, (k.get("camara") or {}).get("deputados", {}), "deputados"),
        ("Senado", "S", sen, (k.get("senado") or {}).get("senadores", {}), "senadores"),
    ):
        legenda, tabela, n = montar_casa(nome_casa, prefixo, lista, cadastro, nome_casa == "Câmara")
        if not n:
            continue
        explica = "Um asterisco e sublinhado marcam o voto contra a orientação do próprio partido. " if nome_casa == "Câmara" else ""
        partes.append(
            f'<section id="{prefixo}"><h2>{"Câmara dos Deputados" if nome_casa == "Câmara" else "Senado Federal"}: {n} {quem}</h2>'
            f'{legenda}<p class="nota">{explica}Votações simbólicas e secretas não têm voto individual e não aparecem aqui.</p>{tabela}</section>'
        )
    doc = (
        f'<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(titulo)}</title>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Serif+4:opsz,wght@8..60,400..650&family=IBM+Plex+Mono:wght@400;500;600&display=swap">'
        f'<style>{ESTILO}</style></head><body>'
        f'<header class="cabecalho"><span class="nota">BOLETIM CÍVICO · ANEXO DE VOTOS</span><h1>{esc(titulo)}</h1>'
        '<p>Para achar um parlamentar, use a busca do seu leitor de PDF (a lupa ou Ctrl+F) e digite o nome. '
        'Cada coluna é uma votação nominal do plenário; a legenda de cada Casa diz qual.</p>'
        f'<p class="nota">Fontes: Câmara dos Deputados, dados abertos; Senado Federal, dados abertos (via servidor MCP senado-br). Coletado em {esc(k.get("coletado_em", "")[:10])}.</p></header>'
        + "".join(partes)
        + "</body></html>"
    )
    with open(a.saida, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"{a.saida}: {len(cam)} votações na Câmara, {len(sen)} no Senado")


if __name__ == "__main__":
    main()
