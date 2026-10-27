#!/usr/bin/env python3
"""Coleta os dados estruturados do boletim semanal.

Busca indicadores no Banco Central (SGS e Focus), a atividade do plenário
da Câmara na semana e os gastos da cota parlamentar (CEAP). Cada fonte é
independente: se uma falhar, o erro vai para "avisos" e as demais seguem.
O resultado é um JSON que o montar.py junta ao conteúdo redigido.

Uso:
    python3 coleta.py --saida coletados.json
    python3 coleta.py --inicio 2026-10-26 --fim 2026-11-01 --deputados "Nikolas Ferreira,Erika Hilton"
"""
import argparse
import datetime as dt
import io
import json
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict

SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={ini}&dataFinal={fim}"
FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
# A API /deputados/{id}/despesas vem vazia desde 2025; o arquivo anual é a fonte que funciona.
CEAP_ANO = "https://www.camara.leg.br/cotas/Ano-{ano}.json.zip"
PLENARIO = 180

# chave: (código SGS, nome, unidade, meses de histórico)
SERIES = {
    "selic_meta": (432, "Meta Selic", "% a.a.", 24),
    "selic_efetiva": (1178, "Selic efetiva", "% a.a.", 3),
    "ipca_mensal": (433, "IPCA no mês", "%", 24),
    "ipca_12m": (13522, "IPCA em 12 meses", "%", 24),
    "dolar": (1, "Dólar comercial (venda)", "R$", 4),
    "ibcbr": (24364, "IBC-Br, com ajuste sazonal", "índice", 24),
    "desocupacao": (24369, "Taxa de desocupação (PNAD)", "%", 24),
    "juros_pf": (20740, "Juros médios do crédito livre a pessoas físicas", "% a.a.", 24),
    "dlsp": (4513, "Dívida líquida do setor público", "% do PIB", 24),
    "dbgg": (13762, "Dívida bruta do governo geral", "% do PIB", 24),
    "primario_12m": (5793, "Resultado primário em 12 meses (déficit +)", "% do PIB", 24),
}

FOCUS_INDICADORES = ["IPCA", "PIB Total", "Selic", "Câmbio", "Resultado primário", "Dívida líquida do setor público"]

avisos = []


def abrir(url, timeout=40):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "consultor-civico/1.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url, tentativas=3, espera=2):
    ultimo = None
    for i in range(tentativas):
        try:
            with abrir(url) as r:
                return json.load(r)
        except Exception as e:  # rede, HTTP ou JSON inválido
            ultimo = e
            time.sleep(espera * (2 ** i))
    raise RuntimeError(f"{url[:120]}: {ultimo}")


def normalizar(nome):
    s = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def br(d):
    return d.strftime("%d/%m/%Y")


def iso_de_br(s):
    return dt.datetime.strptime(s, "%d/%m/%Y").date().isoformat()


def coletar_sgs(hoje):
    saida = {}
    for chave, (codigo, nome, unidade, meses) in SERIES.items():
        ini = hoje - dt.timedelta(days=31 * meses)
        time.sleep(0.5)  # o firewall do BCB recusa rajadas de pedidos
        try:
            dados = get_json(SGS.format(codigo=codigo, ini=br(ini), fim=br(hoje)))
            pontos = [[iso_de_br(x["data"]), float(x["valor"])] for x in dados if x.get("valor") not in (None, "")]
            if not pontos:
                raise RuntimeError("série vazia")
            saida[chave] = {"codigo": codigo, "nome": nome, "unidade": unidade, "pontos": pontos}
        except Exception as e:
            avisos.append(f"Banco Central, série {codigo} ({nome}): {e}")
    return saida


def coletar_focus(hoje):
    filtro = f"Data ge '{(hoje - dt.timedelta(days=14)).isoformat()}' and baseCalculo eq 0"
    q = urllib.parse.urlencode({
        "$filter": filtro, "$orderby": "Data desc", "$top": "500", "$format": "json",
        "$select": "Indicador,IndicadorDetalhe,Data,DataReferencia,Mediana",
    }, quote_via=urllib.parse.quote)  # OData não aceita "+" no lugar de espaço
    try:
        linhas = get_json(f"{FOCUS}?{q}")["value"]
    except Exception as e:
        avisos.append(f"Boletim Focus: {e}")
        return None
    if not linhas:
        avisos.append("Boletim Focus: nenhuma divulgação nas últimas duas semanas")
        return None
    data = max(x["Data"] for x in linhas)
    anos = [str(hoje.year), str(hoje.year + 1)]
    tabela = {}
    for x in linhas:
        if x["Data"] == data and x["Indicador"] in FOCUS_INDICADORES and not x.get("IndicadorDetalhe") and x["DataReferencia"] in anos:
            tabela.setdefault(x["Indicador"], {})[x["DataReferencia"]] = x["Mediana"]
    return {"data": data, "anos": anos, "medianas": tabela}


def camara(caminho, **params):
    """Percorre todas as páginas de um recurso da Câmara."""
    params.setdefault("itens", 100)
    url = f"{CAMARA}/{caminho}?{urllib.parse.urlencode(params)}"
    dados = []
    while url:
        r = get_json(url)
        dados += r.get("dados", [])
        url = next((l["href"] for l in r.get("links", []) if l.get("rel") == "next"), None)
    return dados


def placar(votos):
    c = Counter(v.get("tipoVoto") for v in votos)
    return {"sim": c.get("Sim", 0), "nao": c.get("Não", 0), "abstencao": c.get("Abstenção", 0), "obstrucao": c.get("Obstrução", 0), "total": len(votos)}


def coletar_plenario(inicio, fim, acompanhados):
    saida = {"votacoes": [], "agenda": []}
    try:
        votacoes = camara("votacoes", dataInicio=inicio.isoformat(), dataFim=fim.isoformat(), idOrgao=PLENARIO, ordem="ASC", ordenarPor="dataHoraRegistro")
    except Exception as e:
        avisos.append(f"Câmara, votações do plenário: {e}")
        votacoes = []
    for v in votacoes:
        item = {"id": v["id"], "data": v.get("data"), "descricao": v.get("descricao"), "aprovacao": v.get("aprovacao"), "proposicao": None, "placar": None, "orientacoes": {}, "votos_acompanhados": {}, "contra_orientacao": []}
        try:
            det = get_json(f"{CAMARA}/votacoes/{v['id']}").get("dados", {})
            afetadas = det.get("proposicoesAfetadas") or []
            if afetadas:
                p = afetadas[0]
                item["proposicao"] = {"sigla": f"{p.get('siglaTipo')} {p.get('numero')}/{p.get('ano')}", "ementa": p.get("ementa"), "url": f"https://www.camara.leg.br/propostas-legislativas/{p.get('id')}"}
            votos = get_json(f"{CAMARA}/votacoes/{v['id']}/votos").get("dados", [])
            if votos:  # só votações nominais têm votos individuais
                item["placar"] = placar(votos)
                orient = get_json(f"{CAMARA}/votacoes/{v['id']}/orientacoes").get("dados", [])
                item["orientacoes"] = {o.get("siglaPartidoBloco"): o.get("orientacaoVoto") for o in orient}
                for voto in votos:
                    dep = voto.get("deputado_", {})
                    if normalizar(dep.get("nome")) in acompanhados:
                        item["votos_acompanhados"][dep.get("nome")] = voto.get("tipoVoto")
                    o = item["orientacoes"].get(dep.get("siglaPartido"))
                    if o in ("Sim", "Não") and voto.get("tipoVoto") in ("Sim", "Não") and voto["tipoVoto"] != o:
                        item["contra_orientacao"].append(f"{dep.get('nome')} ({dep.get('siglaPartido')}-{dep.get('siglaUf')})")
        except Exception as e:
            avisos.append(f"Câmara, detalhes da votação {v['id']}: {e}")
        saida["votacoes"].append(item)

    prox_ini, prox_fim = fim + dt.timedelta(days=1), fim + dt.timedelta(days=7)
    try:
        eventos = camara("eventos", dataInicio=prox_ini.isoformat(), dataFim=prox_fim.isoformat(), idOrgao=PLENARIO, ordem="ASC", ordenarPor="dataHoraInicio")
        saida["agenda"] = [{"inicio": e.get("dataHoraInicio"), "tipo": e.get("descricaoTipo"), "descricao": e.get("descricao"), "situacao": e.get("situacao")} for e in eventos]
    except Exception as e:
        avisos.append(f"Câmara, agenda do plenário: {e}")
    return saida


def coletar_ceap(acompanhados, fim):
    """Gastos da cota parlamentar no último mês completo, com ranking e média.

    As notas chegam à Câmara com atraso, então o mês corrente fica de fora.
    """
    mes_ref = fim.replace(day=1) - dt.timedelta(days=1)
    try:
        with abrir(CEAP_ANO.format(ano=mes_ref.year), timeout=300) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        linhas = json.load(z.open(z.namelist()[0]))["dados"]
    except Exception as e:
        avisos.append(f"Câmara, arquivo da cota parlamentar {mes_ref.year}: {e}")
        return None

    def valor(x):
        try:
            return float(x.get("valorLiquido") or 0)
        except ValueError:
            return 0.0

    # Lideranças e órgãos também usam a cota; só entram deputados com UF.
    linhas = [x for x in linhas if x.get("siglaUF") not in ("", "NA", None)]
    no_mes = [x for x in linhas if x.get("mes") == mes_ref.month]
    totais = defaultdict(float)
    for x in no_mes:
        totais[(x["nomeParlamentar"], x.get("siglaPartido"), x["siglaUF"])] += valor(x)
    ranking = sorted(totais.items(), key=lambda t: -t[1])
    media = sum(totais.values()) / len(totais) if totais else 0

    def resumo(nome):
        meus = [x for x in no_mes if normalizar(x["nomeParlamentar"]) == nome]
        ano = sum(valor(x) for x in linhas if normalizar(x["nomeParlamentar"]) == nome)
        por_tipo = defaultdict(float)
        for x in meus:
            por_tipo[x.get("descricao")] += valor(x)
        meus.sort(key=lambda x: -valor(x))
        total = sum(por_tipo.values())
        pos = next((i + 1 for i, ((n, _, _), _) in enumerate(ranking) if normalizar(n) == nome), None)
        return {
            "total_mes": round(total, 2), "total_ano": round(ano, 2), "posicao": pos,
            "por_tipo": sorted(([k, round(v, 2)] for k, v in por_tipo.items()), key=lambda t: -t[1]),
            "maiores": [{"fornecedor": x.get("fornecedor"), "valor": valor(x), "data": (x.get("dataEmissao") or "")[:10], "tipo": x.get("descricao"), "url": x.get("urlDocumento")} for x in meus[:5]],
        }

    return {
        "mes": f"{mes_ref.month:02d}/{mes_ref.year}",
        "deputados_com_gasto": len(totais),
        "media": round(media, 2),
        "ranking": [{"nome": n, "partido": p, "uf": uf, "total": round(t, 2)} for (n, p, uf), t in ranking[:10]],
        "acompanhados": {nome: resumo(nome) for nome in acompanhados},
        "fonte": CEAP_ANO.format(ano=mes_ref.year),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    hoje = dt.date.today()
    seg_passada = hoje - dt.timedelta(days=hoje.weekday() + 7)
    ap.add_argument("--inicio", type=dt.date.fromisoformat, default=seg_passada, help="início da semana (padrão: segunda-feira passada)")
    ap.add_argument("--fim", type=dt.date.fromisoformat, default=seg_passada + dt.timedelta(days=6), help="fim da semana (padrão: domingo passado)")
    ap.add_argument("--deputados", default="", help="nomes parlamentares dos deputados acompanhados, separados por vírgula")
    ap.add_argument("--saida", default="coletados.json")
    a = ap.parse_args()
    acompanhados = [normalizar(d) for d in a.deputados.split(",") if d.strip()]

    resultado = {
        "semana": {"inicio": a.inicio.isoformat(), "fim": a.fim.isoformat()},
        "coletado_em": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "economia": {"series": coletar_sgs(hoje), "focus": coletar_focus(hoje)},
        "camara": coletar_plenario(a.inicio, a.fim, acompanhados),
        "ceap": coletar_ceap(acompanhados, a.fim),
        "avisos": avisos,
    }
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    s = resultado["economia"]["series"]
    print(f"{a.saida}: {len(s)}/{len(SERIES)} séries, {len(resultado['camara']['votacoes'])} votações, {len(resultado['camara']['agenda'])} eventos na agenda, {len(avisos)} avisos")
    for av in avisos:
        print("  aviso:", av, file=sys.stderr)


if __name__ == "__main__":
    main()
