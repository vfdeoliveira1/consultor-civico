#!/usr/bin/env python3
"""Junta os dados coletados e o conteúdo redigido no modelo do boletim diário.

Uso:
    python3 montar.py --coletados coletados.json --conteudo conteudo.json --saida diario.html
"""
import argparse
import datetime as dt
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
SEMANAL = os.path.join(AQUI, "..", "relatorio-semanal")
# Arquivo das edições semanais, para o leitor ir do diário ao semanal.
ARQUIVO_URL = "https://claude.ai/artifact/XQdiMS4ZgKSMxFEKSv8Q5U"
# Nome fixo: a mesma página é republicada todo dia, no mesmo endereço.
TITULO = "Boletim Cívico Diário"


def montar(coletados, conteudo, arquivo_url=ARQUIVO_URL):
    dados = {
        "gerado_em": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "arquivo_url": arquivo_url,
        "temas": json.load(open(os.path.join(SEMANAL, "temas.json"), encoding="utf-8"))["temas"],
        "coletados": coletados,
        "conteudo": conteudo,
    }
    # "</" dentro do JSON fecharia a tag <script> antes da hora.
    bruto = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    modelo = open(os.path.join(AQUI, "modelo.html"), encoding="utf-8").read()
    return modelo.replace("{{TITULO}}", TITULO).replace("{{DADOS}}", bruto)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coletados", required=True)
    ap.add_argument("--conteudo", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    html = montar(json.load(open(a.coletados, encoding="utf-8")), json.load(open(a.conteudo, encoding="utf-8")))
    with open(a.saida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{a.saida}: {len(html) // 1024} KB")


if __name__ == "__main__":
    main()
