# Configurar o site com login

Roteiro para publicar o boletim num Worker da Cloudflare, com acesso só para quem estiver numa lista de e-mails (Cloudflare Access). Os nomes dos menus são os do painel da Cloudflare em outubro de 2026. No painel novo, **Workers & Pages → Create application** cria um Worker, e é ele que serve o site: o Worker entrega os arquivos do branch `site` e aplica o `_headers`, sem código próprio. A configuração fica no `wrangler.jsonc` do branch.

Pré-requisito: o branch `site` já existe no GitHub. Ele é criado pela primeira publicação do `relatorio-semanal/publicar.py`.

## 1. Conta

1. Crie uma conta gratuita em https://dash.cloudflare.com/sign-up.
2. Ligue a verificação em duas etapas: **Manage Account → Authentication → Two-factor authentication**. Faça o mesmo no GitHub, se ainda não estiver ligada.

## 2. Regra de acesso (antes do site ir ao ar)

1. No painel, abra **Zero Trust** (Cloudflare One). Na primeira vez, escolha um nome de equipe e o plano **Free**. Até onde sei, ele cobre até 50 usuários; confira na página de preços. A Cloudflare pode pedir um cartão mesmo no plano gratuito.
2. **Integrations → Identity providers:** confirme que **One-time PIN** está na lista. É o login por código enviado ao e-mail, sem senha para guardar. O provedor "Cloudflare" que vem junto pode ficar: quem entra é decidido pela regra abaixo.
3. **Access controls → Policies → Add a policy:**
   - **Policy name:** Amigos.
   - **Action:** Allow.
   - **Session duration:** 1 week.
   - **Include → Selector: Emails:** o seu e-mail. Os dos amigos entram depois do teste do passo 5.

   Não use "Everyone" nem "Emails ending in", que liberam muito mais gente do que a lista.

## 3. O Worker

1. **Workers & Pages → Create application → Import a repository** (ou **Continue with GitHub**).
2. Autorize o app da Cloudflare no GitHub com **Only select repositories** e marque só `consultor-civico`.
3. **Project name:** `boletim-civico`, igual ao `name` do `wrangler.jsonc`. O endereço fica `boletim-civico.<sua-conta>.workers.dev`.
4. Depois de criado, abra o Worker → **Settings → Build** e confira:
   - **Build command:** vazio.
   - **Deploy command:** `npx wrangler deploy`.
   - **Root directory:** `/`.
   - **Branch control → Production branch:** `site`.
   - **Builds for non-production branches:** desligado.

O primeiro build, se rodar com o `main`, falha: o `main` não tem o `wrangler.jsonc`. Isso não publica nada.

## 4. Ligar o Access no Worker

1. No Worker: **Settings → Domains & Routes**. Na linha do `workers.dev`, abra o menu (`...` ou o lápis) e ligue **Cloudflare Access**. A Cloudflare cria um aplicativo do Access para esse endereço.
2. Em **Zero Trust → Access controls → Applications**, abra o aplicativo criado e, em **Edit**:
   - **Policies:** tire a regra que veio pronta e marque **Amigos**.
   - **Login methods:** só **One-time PIN**. Se aparecer **Instant Auth**, pode ligar.
3. Salve.

Os endereços de prévia por versão ficam desligados no `wrangler.jsonc` (`"preview_urls": false`), então o único endereço do site é o `workers.dev`.

Para tirar alguém, apague o e-mail da regra **Amigos**. Para encerrar o acesso de quem já está logado: **Access controls → Applications → o aplicativo → Revoke existing tokens**.

## 5. Teste antes de mandar o link

Depois do primeiro deploy do branch `site`, rode estes testes numa janela anônima e no terminal, sem login. Troque o endereço e `AAAA-MM-DD` pela data de uma edição publicada:

```bash
SITE=https://boletim-civico.<sua-conta>.workers.dev
for caminho in / /edicoes.json /edicoes/AAAA-MM-DD/ /edicoes/AAAA-MM-DD/boletim.pdf /robots.txt; do
  printf '%-40s ' "$caminho"
  curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "$SITE$caminho"
done
```

O resultado certo é **302 ou 403** em todas as linhas, com redirecionamento para `<equipe>.cloudflareaccess.com`. **Qualquer 200 é um furo**: pare e revise o passo 4.

Depois, com login:

- a página inicial lista as edições;
- o boletim abre e os tópicos funcionam;
- os PDFs baixam;
- um e-mail fora da lista recebe o código, mas não entra.

Confira também os cabeçalhos de segurança: no navegador logado, abra o DevTools (F12) → aba **Rede**, recarregue a página e clique na primeira linha. Em **Cabeçalhos de resposta** devem aparecer `content-security-policy`, `x-frame-options: DENY` e `x-robots-tag: noindex, nofollow`.

## 6. Avisar a sessão semanal

Quando o site estiver no ar e testado, troque a linha **Endereço do site** em `relatorio-semanal/INSTRUCOES.md` pelo endereço do Worker. A partir daí, a resposta de segunda-feira traz o link da edição no site.

## O que cada camada protege

| Camada | Protege contra |
|---|---|
| Cloudflare Access | Qualquer acesso sem login: páginas, PDFs, lista de edições. |
| Prévias desligadas (`preview_urls: false` e builds só do branch `site`) | Endereços paralelos do mesmo site ficarem abertos. |
| `.assetsignore` | O Worker servir arquivos que não são do site (`.git`, configuração). |
| `_headers` | Outro site embutir o boletim (clickjacking), o navegador adivinhar o tipo de arquivo e o endereço vazar para os sites dos links. |
| CSP em cada página | Execução de qualquer script que não seja o do próprio boletim, mesmo se um texto vindo de uma API trouxer código. |
| `robots.txt` e `noindex` | Indexação por buscadores, caso algo fique aberto por engano. |
| App da Cloudflare só neste repositório | A Cloudflare ler outros repositórios seus. |
