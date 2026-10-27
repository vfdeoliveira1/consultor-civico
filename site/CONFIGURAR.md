# Configurar o site com login

Roteiro para publicar o boletim no Cloudflare Pages, com acesso só para quem estiver numa lista de e-mails (Cloudflare Access). Os nomes dos menus são os do painel da Cloudflare em outubro de 2026 e podem mudar; o objetivo de cada passo continua o mesmo.

Pré-requisito: o branch `site` já existe no GitHub. Ele é criado pela primeira publicação do `relatorio-semanal/publicar.py`.

## 1. Conta

1. Crie uma conta gratuita em https://dash.cloudflare.com/sign-up.
2. Ligue a verificação em duas etapas: **Manage Account → Authentication → Two-factor authentication**. Faça o mesmo no GitHub, se ainda não estiver ligada.

## 2. Cloudflare Pages

1. **Workers & Pages → Create → Pages → Connect to Git.**
2. Autorize o app da Cloudflare no GitHub com **Only select repositories** e marque só `consultor-civico`.
3. Configure o projeto:
   - **Project name:** o nome vira o endereço `<nome>.pages.dev`. Evite algo que identifique você ou os seus amigos.
   - **Production branch:** `site`.
   - **Framework preset:** None. **Build command:** vazio. **Build output directory:** `/`.
4. Clique em **Save and Deploy**.
5. Desligue as prévias dos outros branches: **Settings → Builds & deployments → Branch control → Preview branches: None**. Sem isso, cada branch de trabalho (`main`, `claude/...`) vira uma prévia pública com os arquivos do repositório.

**Ainda não mande o endereço para ninguém.** Até o passo 3 terminar, o site está aberto.

## 3. Cloudflare Access (o login)

1. No painel, abra **Zero Trust**. Na primeira vez, escolha um nome de equipe e o plano **Free**. Até onde sei, ele cobre até 50 usuários; confira na página de preços. A Cloudflare pode pedir um cartão mesmo no plano gratuito.
2. **Settings → Authentication → Login methods:** confirme que **One-time PIN** está ativo. É o login por código enviado ao e-mail, sem senha para guardar.
3. **Access → Applications → Add an application → Self-hosted:**
   - **Application name:** Boletim Cívico.
   - **Session duration:** 1 week, ou o que preferir, entre 24 horas e 1 mês.
   - **Application domain:** `<nome>.pages.dev`, com o caminho vazio, para cobrir o site inteiro.
   - Acrescente um segundo domínio: `*.<nome>.pages.dev`, para cobrir também os endereços de cada deploy (`abc123.<nome>.pages.dev`).
4. **Policy:**
   - **Policy name:** Amigos.
   - **Action:** Allow.
   - **Include → Emails:** o seu e-mail e o de cada amigo.

   Não use "Everyone" nem "Emails ending in", que liberam muito mais gente do que a lista.
5. Salve.

Para tirar alguém, apague o e-mail da política. Para encerrar o acesso de quem já está logado: **Access → Applications → Boletim Cívico → Revoke existing tokens**, ou o mesmo pela tela de usuários.

## 4. Teste antes de mandar o link

Rode estes testes numa janela anônima e no terminal, sem login. Troque `<nome>` pelo nome do projeto e `AAAA-MM-DD` pela data de uma edição publicada:

```bash
for caminho in / /edicoes.json /edicoes/AAAA-MM-DD/ /edicoes/AAAA-MM-DD/boletim.pdf /robots.txt; do
  printf '%-40s ' "$caminho"
  curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "https://<nome>.pages.dev$caminho"
done
```

O resultado certo é **302 ou 403** em todas as linhas, com redirecionamento para `<equipe>.cloudflareaccess.com`. **Qualquer 200 é um furo**: pare e revise o passo 3. Repita o teste com o endereço de um deploy específico, que aparece em **Workers & Pages → projeto → Deployments**.

Depois, com login:

- a página inicial lista as edições;
- o boletim abre e os tópicos funcionam;
- os PDFs baixam;
- um e-mail fora da lista recebe o código, mas não entra.

Confira também os cabeçalhos de segurança: no navegador logado, abra o DevTools (F12) → aba **Rede**, recarregue a página e clique na primeira linha. Em **Cabeçalhos de resposta** devem aparecer `content-security-policy`, `x-frame-options: DENY` e `x-robots-tag: noindex, nofollow`.

## 5. Avisar a sessão semanal

Quando o site estiver no ar e testado, troque a linha **Endereço do site** em `relatorio-semanal/INSTRUCOES.md` pelo endereço `https://<nome>.pages.dev`. A partir daí, a resposta de segunda-feira traz o link da edição no site.

## O que cada camada protege

| Camada | Protege contra |
|---|---|
| Cloudflare Access | Qualquer acesso sem login: páginas, PDFs, lista de edições. |
| Prévias desligadas e domínio curinga no Access | Endereços paralelos do mesmo site ficarem abertos. |
| `_headers` | Outro site embutir o boletim (clickjacking), o navegador adivinhar o tipo de arquivo e o endereço vazar para os sites dos links. |
| CSP em cada página | Execução de qualquer script que não seja o do próprio boletim, mesmo se um texto vindo de uma API trouxer código. |
| `robots.txt` e `noindex` | Indexação por buscadores, caso algo fique aberto por engano. |
| App da Cloudflare só neste repositório | A Cloudflare ler outros repositórios seus. |
