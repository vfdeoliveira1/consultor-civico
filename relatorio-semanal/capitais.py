"""Projetos de lei e leis publicadas na semana nas câmaras das capitais.

Chamado pelo coleta.py. Cada câmara é independente: se uma falhar, ela entra
com o erro em "aviso" e as outras seguem. As câmaras sem fonte utilizável
aparecem em SEM_COBERTURA, com o motivo, para a página explicar a ausência.
"""
import concurrent.futures as cf
import datetime as dt
import json
import time
import unicodedata
import urllib.parse
import urllib.request

# Câmaras com SAPL (sistema do Interlegis) e API aberta, conferidas em 27/10/2026.
CAPITAIS_SAPL = {
    "AC": ("Rio Branco", "riobranco.ac"),
    "AM": ("Manaus", "manaus.am"),
    "CE": ("Fortaleza", "fortaleza.ce"),
    "PB": ("João Pessoa", "joaopessoa.pb"),
    "RN": ("Natal", "natal.rn"),
    "RO": ("Porto Velho", "portovelho.ro"),
    "RR": ("Boa Vista", "boavista.rr"),
    "TO": ("Palmas", "palmas.to"),
}
SAO_PAULO_WS = "https://splegisws.saopaulo.sp.leg.br/ws/ws2.asmx"

# Resultado do levantamento de 27/10/2026. Atualize quando uma câmara passar a responder.
SEM_COBERTURA = [
    ["BA", "Salvador", "o sistema legislativo só tem endereço numérico (45.4.247.157), que a rede do ambiente não permite liberar"],
    ["DF", "Câmara Legislativa do DF", "o site recusa conexões vindas da nuvem"],
    ["RJ", "Rio de Janeiro", "certificado de segurança incompleto no site"],
    ["MG", "Belo Horizonte", "sem dados abertos; só páginas para leitura"],
    ["PR", "Curitiba", "sem dados abertos; só páginas para leitura"],
    ["RS", "Porto Alegre", "o site não respondeu a tempo"],
    ["PE", "Recife", "o SAPL respondeu fora do ar (erro 503)"],
    ["GO", "Goiânia", "o SAPL tem certificado de segurança inválido"],
    ["AL", "Maceió", "o site recusa conexões vindas da nuvem"],
    ["PI", "Teresina", "o site recusa conexões vindas da nuvem"],
    ["MS", "Campo Grande", "o site recusa conexões vindas da nuvem"],
    ["PA", "Belém", "o site recusa conexões vindas da nuvem"],
    ["SC", "Florianópolis", "o site recusa conexões vindas da nuvem"],
    ["ES", "Vitória", "o site recusa conexões vindas da nuvem"],
    ["MA", "São Luís", "o site recusa conexões vindas da nuvem"],
    ["AP", "Macapá", "não foi encontrada a área de projetos no site"],
    ["MT", "Cuiabá", "não foi encontrada a área de projetos no site"],
    ["SE", "Aracaju", "não foi encontrada a área de projetos no site"],
]


def _get_json(url, timeout=60, tentativas=3):
    ultimo = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "consultor-civico/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            ultimo = e
            time.sleep(2 * (2 ** i))
    raise RuntimeError(f"{url[:100]}: {ultimo}")


def _norm(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def _principal(descricao):
    """Projetos de lei e emendas à Lei Orgânica; o resto (indicações, moções, requerimentos) vira contagem."""
    d = _norm(descricao)
    return "projeto de lei" in d or "lei organica" in d


def _sapl(uf, cidade, host, inicio, fim):
    base = f"https://sapl.{host}.leg.br"
    saida = {"uf": uf, "cidade": cidade, "fonte": "SAPL", "url": base, "projetos": [], "outros": {}, "leis": [], "aviso": None}
    tipos = {t["id"]: t.get("descricao") or t.get("sigla") for t in _get_json(f"{base}/api/materia/tipomaterialegislativa/?page_size=100")["results"]}
    url = f"{base}/api/materia/materialegislativa/?" + urllib.parse.urlencode({"data_apresentacao__gte": inicio.isoformat(), "data_apresentacao__lte": fim.isoformat(), "page_size": 100})
    materias = []
    while url:
        r = _get_json(url)
        materias += r.get("results", [])
        prox = (r.get("pagination") or {}).get("links", {}).get("next")
        url = prox.replace("http://", "https://") if prox else None
    autores, partidos = {}, {}

    def autor(aid):
        if aid not in autores:
            a = _get_json(f"{base}/api/base/autor/{aid}")
            autores[aid] = a.get("nome") or a.get("__str__")
            if a.get("tipo") == 1 and a.get("object_id"):  # tipo 1: parlamentar da casa
                try:
                    f = _get_json(f"{base}/api/parlamentares/filiacao/?parlamentar={a['object_id']}")["results"]
                    atual = [x for x in f if not x.get("data_desfiliacao")]
                    if atual:
                        partidos[aid] = atual[0]["__str__"].split(" - ")[1]
                except Exception:
                    pass
        return autores[aid], partidos.get(aid)

    for m in sorted(materias, key=lambda x: (x.get("data_apresentacao") or "", x.get("numero") or 0)):
        desc = tipos.get(m.get("tipo"), "Outro")
        if not _principal(desc):
            saida["outros"][desc] = saida["outros"].get(desc, 0) + 1
            continue
        nomes = []
        for aid in m.get("autores") or []:
            try:
                n, p = autor(aid)
                nomes.append(f"{n} ({p})" if p else n)
            except Exception:
                pass
        saida["projetos"].append({
            "tipo": desc, "numero": m.get("numero"), "ano": m.get("ano"), "data": m.get("data_apresentacao"),
            "ementa": (m.get("ementa") or "").strip(), "autores": nomes, "url": f"{base}/materia/{m['id']}",
        })
    # Leis publicadas: a API não filtra por data, então lê as 50 mais recentes e fica com as da semana.
    try:
        r = _get_json(f"{base}/api/norma/normajuridica/?o=-data&page_size=50")
        for n in r.get("results", []):
            if not (n.get("data") and inicio.isoformat() <= n["data"] <= fim.isoformat()):
                continue
            # Decretos legislativos e resoluções costumam ser homenagens; entram só na contagem.
            if not _norm(n.get("__str__")).startswith("lei"):
                saida["outros"]["Decretos legislativos e outras normas publicadas"] = saida["outros"].get("Decretos legislativos e outras normas publicadas", 0) + 1
                continue
            saida["leis"].append({"titulo": n.get("__str__"), "data": n.get("data"), "ementa": (n.get("ementa") or "").strip(), "url": f"{base}/norma/{n['id']}"})
    except Exception as e:
        saida["aviso"] = f"leis publicadas não consultadas: {e}"
    return saida


def _sao_paulo(inicio, fim):
    saida = {"uf": "SP", "cidade": "São Paulo", "fonte": "SPLegis", "url": "https://splegisconsulta.saopaulo.sp.leg.br/", "projetos": [], "outros": {}, "leis": [], "aviso": None}
    tipos = {t["sigla"]: t["nome"].capitalize() for t in _get_json(f"{SAO_PAULO_WS}/TiposDeMateriaJSON")}
    materias = []
    for ano in sorted({inicio.year, fim.year}):
        materias += _get_json(f"{SAO_PAULO_WS}/ProjetosPorAnoJSON?Ano={ano}", timeout=180)
    for m in materias:
        if not (inicio.isoformat() <= (m.get("data") or "")[:10] <= fim.isoformat()):
            continue
        sigla = m.get("tipo")
        if sigla not in ("PL", "PLO"):
            nome = tipos.get(sigla, sigla)
            saida["outros"][nome] = saida["outros"].get(nome, 0) + 1
            continue
        nomes = []
        try:
            r = _get_json(f"{SAO_PAULO_WS}/ProjetosAutoresJSON?" + urllib.parse.urlencode({"ano": m["ano"], "tipo": sigla, "numero": m["numero"]}))
            nomes = [a["nome"].title() for item in r for a in item.get("autores") or []]
        except Exception:
            pass
        saida["projetos"].append({
            "tipo": "Projeto de Lei" if sigla == "PL" else "Projeto de Emenda à Lei Orgânica",
            "numero": m.get("numero"), "ano": m.get("ano"), "data": (m.get("data") or "")[:10],
            "ementa": (m.get("ementa") or "").strip(), "autores": nomes, "url": "https://splegisconsulta.saopaulo.sp.leg.br/Pesquisa/IndexProjeto",
        })
    saida["projetos"].sort(key=lambda p: (p["data"], p["numero"] or 0))
    return saida


def coletar_capitais(inicio, fim, avisos):
    tarefas = [("SP", "São Paulo", lambda: _sao_paulo(inicio, fim))]
    tarefas += [(uf, c, (lambda uf=uf, c=c, h=h: _sapl(uf, c, h, inicio, fim))) for uf, (c, h) in CAPITAIS_SAPL.items()]
    camaras = []
    with cf.ThreadPoolExecutor(6) as ex:
        futuros = {ex.submit(f): (uf, c) for uf, c, f in tarefas}
        for fut in cf.as_completed(futuros):
            uf, c = futuros[fut]
            try:
                camaras.append(fut.result())
            except Exception as e:
                avisos.append(f"Câmara Municipal de {c} ({uf}): {e}")
                camaras.append({"uf": uf, "cidade": c, "projetos": [], "outros": {}, "leis": [], "aviso": f"não foi possível consultar: {str(e)[:160]}"})
    camaras.sort(key=lambda x: -len(x["projetos"]))
    return {"camaras": camaras, "sem_cobertura": SEM_COBERTURA, "levantamento": "2026-10-27"}
