#!/usr/bin/env python3
"""Junta os dados coletados e o conteúdo redigido no modelo HTML do boletim.

Uso:
    python3 montar.py --coletados coletados.json --conteudo conteudo.json --saida boletim.html
"""
import argparse
import datetime as dt
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
# Página fixa com todas as edições (arquivo.html publicado); cada edição nova é registrada no banco dela.
ARQUIVO_URL = "https://claude.ai/artifact/XQdiMS4ZgKSMxFEKSv8Q5U"


def reduzir(pontos, maximo=160):
    """Séries diárias longas viram uma amostra regular, mantendo o último ponto."""
    if len(pontos) <= maximo:
        return pontos
    passo = len(pontos) / maximo
    amostra = [pontos[int(i * passo)] for i in range(maximo)]
    if amostra[-1] != pontos[-1]:
        amostra.append(pontos[-1])
    return amostra


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coletados", required=True)
    ap.add_argument("--conteudo", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()

    coletados = json.load(open(a.coletados, encoding="utf-8"))
    conteudo = json.load(open(a.conteudo, encoding="utf-8"))
    for serie in coletados.get("economia", {}).get("series", {}).values():
        serie["pontos"] = reduzir(serie["pontos"])

    fim = dt.date.fromisoformat(coletados["semana"]["fim"])
    ano, semana, _ = fim.isocalendar()
    agora = dt.datetime.now().astimezone()
    dados = {
        "edicao": f"{semana}/{ano}",
        "gerado_em": agora.isoformat(timespec="minutes"),
        "arquivo_url": ARQUIVO_URL,
        "temas": json.load(open(os.path.join(AQUI, "temas.json"), encoding="utf-8"))["temas"],
        "coletados": coletados,
        "conteudo": conteudo,
    }
    # "</" dentro do JSON fecharia a tag <script> antes da hora.
    bruto = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    modelo = open(os.path.join(AQUI, "modelo.html"), encoding="utf-8").read()
    titulo = f"Boletim Cívico {agora:%d/%m/%Y}"
    html = modelo.replace("{{TITULO}}", titulo).replace("{{DADOS}}", bruto)
    with open(a.saida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{a.saida}: {len(html) // 1024} KB, título \"{titulo}\"")


if __name__ == "__main__":
    main()
