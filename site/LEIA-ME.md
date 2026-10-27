# Site do Boletim Cívico

Esta pasta é o modelo do site publicado num Worker da Cloudflare (arquivos estáticos, sem código). O site em si fica no branch `site`, que o `relatorio-semanal/publicar.py` monta a cada edição:

```
index.html                  arquivo de edições (gerado de relatorio-semanal/arquivo.html)
edicoes.json                lista das edições, lida pelo index.html
edicoes/AAAA-MM-DD/
  index.html                boletim da semana
  boletim.pdf               PDF do boletim
  votos.pdf                 PDF com o voto de cada parlamentar
_headers                    cabeçalhos de segurança (copiado desta pasta)
robots.txt                  pede aos buscadores que não indexem (copiado desta pasta)
wrangler.jsonc              configuração do Worker: nome, pasta dos arquivos, prévias desligadas
.assetsignore               arquivos do branch que o Worker não serve (.git, configuração)
```

Não edite o branch `site` à mão: mude esta pasta ou os modelos em `relatorio-semanal/` e deixe a próxima edição levar a mudança. O login fica no Cloudflare Access, fora do repositório; o passo a passo está em `CONFIGURAR.md`.
