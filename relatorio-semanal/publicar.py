#!/usr/bin/env python3
"""Publica uma edição no site do boletim (branch `site`, servido pelo Cloudflare Pages atrás do login).

Monta o boletim com o endereço do arquivo do próprio site, copia os PDFs, atualiza a lista de
edições e a página inicial, grava a política de segurança de cada página e faz commit e push.

Uso:
    python3 publicar.py --coletados coletados.json --conteudo conteudo.json \\
        --pdf boletim.pdf [--votos-pdf votos.pdf] [--teste] [--sem-push]

Saída 0: publicado (ou só commitado, com --sem-push). Saída 4: o push foi recusado ou falhou.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

from montar import montar

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
MODELO_SITE = os.path.join(RAIZ, "site")

# Scripts só do próprio site e com o hash exato dos que estão na página; estilos e fontes do Google Fonts.
CSP = ("default-src 'none'; script-src 'self' {hashes}; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'")
SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)


def git(*args, cwd=RAIZ, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)} falhou:\n{r.stderr.strip()}")
    return r


def hashes(html):
    """sha256 de cada script embutido que o navegador executa (o bloco de dados JSON não entra)."""
    saida = []
    for attrs, corpo in SCRIPT.findall(html):
        if "src=" in attrs:
            continue
        tipo = re.search(r'type\s*=\s*"([^"]*)"', attrs)
        if tipo and "javascript" not in tipo.group(1) and tipo.group(1) != "module":
            continue
        saida.append("'sha256-" + base64.b64encode(hashlib.sha256(corpo.encode("utf-8")).digest()).decode() + "'")
    return " ".join(sorted(set(saida)))


def pagina(fragmento):
    """Os modelos são fragmentos (o claude.ai acrescenta o esqueleto); no site a página precisa dele."""
    csp = CSP.format(hashes=hashes(fragmento))
    return ("<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta http-equiv=\"Content-Security-Policy\" content=\"{csp}\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n<link rel=\"icon\" href=\"data:,\">\n"
            + fragmento + "\n</html>\n")


def preparar(pasta, branch):
    """Abre o branch do site numa pasta à parte (worktree), sem mexer no branch de trabalho."""
    if os.path.exists(pasta):
        git("worktree", "remove", "--force", pasta, check=False)
        shutil.rmtree(pasta, ignore_errors=True)
    git("worktree", "prune")
    existe = git("fetch", "origin", branch, check=False).returncode == 0
    if existe:
        git("worktree", "add", "--force", "-B", branch, pasta, f"origin/{branch}")
    else:
        print(f"O branch {branch} ainda não existe no GitHub: criando do zero.")
        git("branch", "-D", branch, check=False)
        git("worktree", "add", "--orphan", "-b", branch, pasta)


def enviar(pasta, branch):
    for espera in (0, 2, 4, 8, 16):
        time.sleep(espera)
        r = git("push", "-u", "origin", branch, cwd=pasta, check=False)
        if r.returncode == 0:
            return True
        erro = r.stderr.strip()
        print(f"push falhou: {erro.splitlines()[-1] if erro else r.returncode}")
        # Recusa de permissão não melhora tentando de novo.
        if re.search(r"403|denied|not allowed|forbidden|protected", erro, re.I):
            break
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coletados", required=True)
    ap.add_argument("--conteudo", required=True)
    ap.add_argument("--pdf", required=True, help="PDF do boletim, gerado pelo pdf.js")
    ap.add_argument("--votos-pdf", help="PDF dos votos; omita quando o votos.py sair com código 3")
    ap.add_argument("--teste", action="store_true", help="marca a edição como teste no arquivo")
    ap.add_argument("--pasta", default="/tmp/boletim/site", help="onde abrir o branch do site")
    ap.add_argument("--branch", default="site")
    ap.add_argument("--sem-push", action="store_true", help="faz o commit e para antes do push")
    a = ap.parse_args()

    coletados = json.load(open(a.coletados, encoding="utf-8"))
    conteudo = json.load(open(a.conteudo, encoding="utf-8"))
    inicio, fim = coletados["semana"]["inicio"], coletados["semana"]["fim"]

    preparar(a.pasta, a.branch)
    site = a.pasta
    for nome in os.listdir(MODELO_SITE):
        if not nome.endswith(".md"):
            shutil.copy(os.path.join(MODELO_SITE, nome), os.path.join(site, nome))

    destino = os.path.join(site, "edicoes", inicio)
    os.makedirs(destino, exist_ok=True)
    html, titulo = montar(coletados, conteudo, arquivo_url="/")
    open(os.path.join(destino, "index.html"), "w", encoding="utf-8").write(pagina(html))
    shutil.copy(a.pdf, os.path.join(destino, "boletim.pdf"))
    if a.votos_pdf:
        shutil.copy(a.votos_pdf, os.path.join(destino, "votos.pdf"))
    elif os.path.exists(os.path.join(destino, "votos.pdf")):
        os.remove(os.path.join(destino, "votos.pdf"))

    arquivo = open(os.path.join(AQUI, "arquivo.html"), encoding="utf-8").read()
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(pagina(arquivo))

    caminho_lista = os.path.join(site, "edicoes.json")
    lista = json.load(open(caminho_lista, encoding="utf-8")) if os.path.exists(caminho_lista) else []
    cam = (coletados.get("camara") or {}).get("votacoes", [])
    sen = (coletados.get("senado") or {}).get("votacoes", [])
    ano, semana, _ = dt.date.fromisoformat(fim).isocalendar()
    base = f"/edicoes/{inicio}/"
    entrada = {
        "inicio": inicio, "fim": fim, "edicao": f"{semana}/{ano}", "publicado_em": dt.date.today().isoformat(),
        "titulo": titulo, "url": base, "pdf": base + "boletim.pdf", "votos_pdf": base + "votos.pdf" if a.votos_pdf else None,
        "teste": a.teste, "votacoes_nominais": len([v for v in cam if v.get("votos")]) + len(sen),
        "destaques": [d.get("texto", "") for d in conteudo.get("destaques", [])[:3]],
    }
    lista = sorted([e for e in lista if e.get("inicio") != inicio] + [entrada], key=lambda e: e["inicio"], reverse=True)
    json.dump(lista, open(caminho_lista, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    git("add", "-A", cwd=site)
    if git("diff", "--cached", "--quiet", cwd=site, check=False).returncode == 0:
        print("Nada mudou no site.")
        return
    git("commit", "-q", "-m", f"Edição de {inicio} a {fim}" + (" (teste)" if a.teste else ""), cwd=site)
    print(f"Commit no branch {a.branch}: edicoes/{inicio}/, {len(lista)} edições no arquivo.")
    if a.sem_push:
        print(f"--sem-push: nada enviado. Pasta: {site}")
        return
    if not enviar(site, a.branch):
        print(f"Não foi possível enviar o branch {a.branch}. A edição continua no claude.ai.")
        sys.exit(4)
    print(f"Publicado: branch {a.branch}, endereço {base}")


if __name__ == "__main__":
    main()
