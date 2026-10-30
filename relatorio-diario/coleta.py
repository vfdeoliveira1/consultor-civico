#!/usr/bin/env python3
"""Coleta os dados do boletim diário: poucos indicadores, as votações do dia anterior e a pauta de hoje.

Reaproveita as funções do relatorio-semanal/coleta.py, com menos séries e sem o voto de cada
parlamentar, para a página ficar leve. Cada fonte é independente: o que falha vira aviso.

Uso:
    python3 coleta.py --saida coletados.json            # dia anterior
    python3 coleta.py --dia 2026-10-29 --saida coletados.json
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "relatorio-semanal"))
import coleta as semanal  # noqa: E402

# Só o que muda de um dia para o outro ou que o leitor quer ver todo dia; meses de histórico curtos.
SERIES = {
    "selic_meta": (432, "Meta Selic", "% a.a.", 3),
    "dolar": (1, "Dólar comercial (venda)", "R$", 2),
    "ipca_12m": (13522, "IPCA em 12 meses", "%", 3),
}


def enxugar_camara(c):
    """Placar e orientação bastam no diário; os votos nominais ficam no boletim semanal."""
    vistas = []
    for v in c["votacoes"]:
        if not v.get("proposicao"):
            continue
        vistas.append({k: v.get(k) for k in ("data", "descricao", "aprovacao", "proposicao", "placar")} | {"contra_orientacao": len(v.get("contra_orientacao") or [])})
    return {"votacoes": vistas, "agenda": c["agenda"]}


def enxugar_senado(s):
    return {"votacoes": [{k: v.get(k) for k in ("data", "materia", "ementa", "descricao", "resultado", "secreta", "placar", "url")} for v in s["votacoes"]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ontem = dt.date.today() - dt.timedelta(days=1)
    ap.add_argument("--dia", type=dt.date.fromisoformat, default=ontem, help="dia coberto (padrão: ontem)")
    ap.add_argument("--saida", default="coletados.json")
    a = ap.parse_args()
    hoje = a.dia + dt.timedelta(days=1)

    semanal.SERIES = SERIES
    # Na API da Câmara, dataInicio igual a dataFim volta vazio: pede até hoje e fica só com o dia coberto.
    camara = semanal.coletar_plenario(a.dia, hoje, [])
    camara["votacoes"] = [v for v in camara["votacoes"] if (v.get("data") or "")[:10] == a.dia.isoformat()]
    try:
        eventos = semanal.camara("eventos", dataInicio=hoje.isoformat(), dataFim=(hoje + dt.timedelta(days=1)).isoformat(),
                                 idOrgao=semanal.PLENARIO, ordem="ASC", ordenarPor="dataHoraInicio")
        camara["agenda"] = [{"inicio": e.get("dataHoraInicio"), "tipo": e.get("descricaoTipo"), "descricao": e.get("descricao"), "situacao": e.get("situacao")}
                            for e in eventos if (e.get("dataHoraInicio") or "")[:10] == hoje.isoformat()]
    except Exception as e:
        semanal.avisos.append(f"Câmara, pauta de hoje: {e}")
        camara["agenda"] = []
    resultado = {
        "dia": a.dia.isoformat(),
        "hoje": hoje.isoformat(),
        "coletado_em": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "economia": {"series": semanal.coletar_sgs(a.dia), "focus": semanal.coletar_focus(a.dia)},
        "camara": enxugar_camara(camara),
        "senado": enxugar_senado(semanal.coletar_senado(a.dia, a.dia)),
        "avisos": semanal.avisos,
    }
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    print(f"{a.saida}: {len(resultado['economia']['series'])}/{len(SERIES)} séries, "
          f"{len(resultado['camara']['votacoes'])} votações na Câmara, {len(resultado['senado']['votacoes'])} no Senado, "
          f"{len(resultado['camara']['agenda'])} eventos hoje no plenário da Câmara, {len(semanal.avisos)} avisos")
    for av in semanal.avisos:
        print("  aviso:", av, file=sys.stderr)


if __name__ == "__main__":
    main()
