"""Atividade da semana de todos os deputados federais e senadores em exercício.

Chamado pelo coleta.py, para a consulta por parlamentar da página: discursos,
proposições apresentadas (como autor ou coautor) e, no Senado, a cota
parlamentar do ano. Os votos já vêm de coletar_plenario e coletar_senado, e a
cota dos deputados, de coletar_ceap.

Tudo é guardado em listas compactas, com índices em vez de textos repetidos,
porque vai embutido na página.
"""
import concurrent.futures as cf
import re
import urllib.parse

LIMITE_TEXTO = 400


def _curto(t, n=LIMITE_TEXTO):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _norm(t, normalizar):
    return normalizar(re.sub(r"^(senador|senadora)\s+", "", (t or "").strip(), flags=re.I))


def atividade_camara(inicio, fim, avisos, get_json, camara, base):
    saida = {"deputados": {}, "discursos": {}, "proposicoes": [], "autoria": {}}
    try:
        for d in camara("deputados", ordem="ASC", ordenarPor="nome"):
            saida["deputados"][str(d["id"])] = [d.get("nome"), d.get("siglaPartido"), d.get("siglaUf")]
    except Exception as e:
        avisos.append(f"Câmara, lista de deputados: {e}")
        return saida

    def discursos(dep_id):
        r = get_json(f"{base}/deputados/{dep_id}/discursos?" + urllib.parse.urlencode({"dataInicio": inicio.isoformat(), "dataFim": fim.isoformat(), "itens": 100}))
        return dep_id, [[(x.get("dataHoraInicio") or "")[:16], x.get("tipoDiscurso"), (x.get("faseEvento") or {}).get("titulo"), _curto(x.get("sumario")), x.get("urlTexto")] for x in r.get("dados", [])]

    falhas = 0
    with cf.ThreadPoolExecutor(8) as ex:
        for fut in cf.as_completed([ex.submit(discursos, i) for i in saida["deputados"]]):
            try:
                dep_id, lista = fut.result()
                if lista:
                    saida["discursos"][dep_id] = lista
            except Exception:
                falhas += 1
    if falhas:
        avisos.append(f"Câmara: discursos de {falhas} deputados não puderam ser consultados.")

    try:
        props = camara("proposicoes", dataApresentacaoInicio=inicio.isoformat(), dataApresentacaoFim=fim.isoformat(), ordem="ASC", ordenarPor="id")
    except Exception as e:
        avisos.append(f"Câmara, proposições da semana: {e}")
        return saida

    def autores(p):
        r = get_json(f"{base}/proposicoes/{p['id']}/autores")
        ids = []
        for a in r.get("dados", []):
            m = re.search(r"/deputados/(\d+)", a.get("uri") or "")
            if m:
                ids.append(m.group(1))
        return p, ids

    falhas = 0
    with cf.ThreadPoolExecutor(8) as ex:
        resultados = []
        for fut in cf.as_completed([ex.submit(autores, p) for p in props]):
            try:
                resultados.append(fut.result())
            except Exception:
                falhas += 1
    for p, ids in sorted(resultados, key=lambda t: t[0]["id"]):
        if not ids:
            continue
        idx = len(saida["proposicoes"])
        saida["proposicoes"].append([p.get("siglaTipo"), p.get("numero"), p.get("ano"), (p.get("dataApresentacao") or "")[:10], _curto(p.get("ementa"), 300), f"https://www.camara.leg.br/propostas-legislativas/{p['id']}"])
        for i in ids:
            saida["autoria"].setdefault(i, []).append(idx)
    if falhas:
        avisos.append(f"Câmara: autores de {falhas} proposições não puderam ser consultados.")
    return saida


def atividade_senado(inicio, fim, avisos, mcp, normalizar):
    saida = {"senadores": {}, "discursos": {}, "materias": [], "autoria": {}, "ceaps_ano": {}, "ano_ceaps": fim.year}
    try:
        for s in mcp.chamar("senado_listar_senadores").get("senadores", []):
            saida["senadores"][str(s["codigo"])] = [s.get("nome"), s.get("partido"), s.get("uf")]
    except Exception as e:
        avisos.append(f"Senado, lista de senadores: {e}")
        return saida
    try:
        d = mcp.chamar("senado_discursos_plenario", dataInicio=inicio.strftime("%Y%m%d"), dataFim=fim.strftime("%Y%m%d"))
        for x in d.get("discursos", []):
            cod = str(x.get("codigoParlamentar"))
            saida["discursos"].setdefault(cod, []).append([x.get("data"), x.get("tipoUsoPalavra"), x.get("casa"), _curto(x.get("resumo")), x.get("url")])
    except Exception as e:
        avisos.append(f"Senado, discursos do plenário: {e}")
    try:
        r = mcp.chamar("senado_buscar_materias", dataInicioApresentacao=inicio.strftime("%Y%m%d"), dataFimApresentacao=fim.strftime("%Y%m%d"), limite=500)
        por_nome = {_norm(v[0], normalizar): cod for cod, v in saida["senadores"].items()}
        for m in r.get("materias", []):
            # O autor vem como texto ("Senador Fulano (PL/RN)"); só entram as de senadores em exercício.
            nome = _norm((m.get("autor") or "").split("(")[0], normalizar)
            cod = por_nome.get(nome)
            if not cod:
                continue
            idx = len(saida["materias"])
            url = f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{m['codigo']}" if m.get("codigo") else m.get("url")
            saida["materias"].append([m.get("sigla"), m.get("numero"), m.get("ano"), m.get("dataApresentacao"), _curto(m.get("ementa"), 300), url])
            saida["autoria"].setdefault(cod, []).append(idx)
    except Exception as e:
        avisos.append(f"Senado, matérias apresentadas: {e}")
    try:
        s = mcp.chamar("senado_ceaps", ano=fim.year, modo="por-senador")
        for x in s.get("agregado", []):
            if str(x.get("chave")) in saida["senadores"]:
                saida["ceaps_ano"][str(x["chave"])] = round(x.get("total") or 0, 2)
    except Exception as e:
        avisos.append(f"Senado, cota parlamentar (CEAPS): {e}")
    return saida
