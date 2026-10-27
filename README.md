# consultor-civico

Configuração para usar uma IA como assistente de legislação e política brasileira. O projeto tem duas partes:

1. **Assistente de perguntas:** responde sobre política, economia, justiça e direito **pesquisando no texto das leis e em fontes oficiais**, e não de memória, e cita a norma, o artigo e o link oficial.
2. **Boletim Cívico semanal:** toda segunda-feira, uma tarefa agendada monta e publica uma página com o que aconteceu na semana anterior no governo federal, no Congresso, na economia e nas câmaras das capitais. Junto vêm um PDF do boletim e um PDF com o voto de cada deputado e senador.

O conteúdo das leis não fica neste repositório. Ele vem do acervo público [`ctresb/leis`](https://github.com/ctresb/leis), que tem a legislação brasileira convertida para Markdown, com um arquivo por norma. Aqui ficam as instruções para a IA, a configuração dos servidores MCP, o script que baixa o acervo e o código do boletim.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `CLAUDE.md` | Instruções para a IA: como pesquisar no acervo, citar fontes, conferir a vigência e quando usar fontes externas (Senado, Câmara, Banco Central, IBGE, DataJud). |
| `.mcp.json` | Servidores MCP que o Claude Code carrega ao iniciar: `senado-br` (proposições e votações do Senado) e `bcb-br` (Selic, IPCA, câmbio). O `bcb-br` tem `NODE_USE_ENV_PROXY=1` para funcionar atrás do proxy da nuvem. |
| `setup.sh` | Instala o `ripgrep`, baixa o acervo de leis em `~/leis` e pré-instala o MCP do Banco Central. |
| `relatorio-semanal/` | Código e instruções do Boletim Cívico (detalhes abaixo). |

## Boletim Cívico semanal

### O que o boletim traz

A página abre com os botões dos tópicos. Cada botão mostra um tópico, e no fim dele os botões aparecem de novo.

| Tópico | Conteúdo |
|---|---|
| O que importa nesta semana | 4 a 6 destaques. |
| Economia | Selic, IPCA, dólar, desemprego, juros ao consumidor e dívida pública, com gráficos, mais as projeções do boletim Focus e uma análise. |
| Congresso e leis | Leis e PECs da semana, comparadas com o texto anterior no acervo, e cada votação nominal da Câmara e do Senado com placar, orientação dos partidos e votos por partido e por parlamentar. |
| Consultar um parlamentar | Busca por nome de qualquer deputado federal ou senador em exercício: votos nas votações nominais (com aviso de voto contra o partido), discursos, proposições apresentadas e cota parlamentar da semana. |
| Deputados que você acompanha | Sandro Filho (PP-BA) e Paulo Câmara (PL-BA), com fatos verificáveis e gastos da cota parlamentar. |
| Deputados em evidência | Os mais citados na imprensa de linhas editoriais diferentes, mais o ranking da cota parlamentar. |
| Presidente e governo federal | Sanções, vetos, medidas provisórias, decretos, agenda e vetos à espera do Congresso. |
| STF e tribunais superiores | Decisões de efeito geral. |
| Câmaras das capitais | Projetos de lei e leis publicadas nas capitais com dados abertos, com busca por vereador. |
| Bahia e Salvador | Resumo curto do que tem ligação com o governo federal. |
| Agenda da próxima semana | Pauta do plenário da Câmara, Copom, julgamentos e outros eventos. |
| Para entender | Um tema da semana explicado, com os artigos de lei. |

Os fatos de deputados levam selos com critérios fixos: **Entrega**, **Ponto de atenção** e **Registro**. A avaliação política aparece sempre com os dois lados. O rodapé lista o que não foi possível consultar na semana.

### Como ele roda

Uma tarefa agendada no claude.ai roda **toda segunda-feira às 7h39** (horário de Brasília), para o boletim chegar por volta das 8h. A cada disparo, uma sessão nova:

1. clona este repositório e prepara o acervo;
2. pesquisa a semana anterior e escolhe os deputados em evidência;
3. roda `relatorio-semanal/coleta.py`, que busca os dados estruturados;
4. escreve o conteúdo da semana num `conteudo.json`, no formato de `relatorio-semanal/exemplo.json`;
5. monta a página com `montar.py` e a publica como página privada no claude.ai;
6. registra a edição no arquivo de edições anteriores;
7. gera os PDFs com `pdf.js` e `votos.py` e os envia ao leitor, com notificação no celular.

O passo a passo completo e as regras de redação estão em [`relatorio-semanal/INSTRUCOES.md`](relatorio-semanal/INSTRUCOES.md). **Para mudar o boletim** (deputados acompanhados, seções, fontes, tom), edite esse arquivo: a tarefa agendada só manda segui-lo.

### Arquivos do boletim

| Arquivo | Para que serve |
|---|---|
| `INSTRUCOES.md` | Configuração e passo a passo da sessão semanal. |
| `coleta.py` | Coleta os dados de cada fonte, de forma independente: uma fonte que falha vira aviso e as demais seguem. Fontes: séries do Banco Central e o Focus; votações, votos e agenda do plenário da Câmara; votações, votos e vetos do Senado, pelo servidor MCP `senado-br`; e cota parlamentar, pelo arquivo anual da Câmara, porque a API de despesas vem vazia. |
| `atividade.py` | Discursos, proposições apresentadas e, no Senado, cota do ano de todos os deputados e senadores em exercício, para a consulta por parlamentar. |
| `capitais.py` | Projetos de lei e leis das câmaras das capitais. Traz a lista das câmaras cobertas e das que ficaram de fora, com o motivo. |
| `montar.py` | Junta os dados coletados e o conteúdo redigido no `modelo.html`. |
| `modelo.html` | A página do boletim: tabelas, gráficos em SVG, temas claro e escuro, layout de celular e navegação por tópicos. |
| `pdf.js` | Gera o PDF do boletim (A4, tema claro, todos os tópicos em sequência). |
| `votos.py` | Monta o PDF "Votos da semana": todos os deputados e senadores em ordem alfabética, com o voto em cada votação nominal, para consultar com a busca do leitor de PDF. |
| `exemplo.json` | Formato do conteúdo semanal, com textos de exemplo. |
| `arquivo.html` | Página fixa com todas as edições, publicada em https://claude.ai/artifact/XQdiMS4ZgKSMxFEKSv8Q5U. Ela lê a lista do próprio banco de dados, e a sessão semanal só acrescenta a edição nova. |

Para gerar um boletim à mão, para uma semana específica:

```bash
cd relatorio-semanal
python3 coleta.py --inicio 2026-10-12 --fim 2026-10-18 --deputados "Nome 1,Nome 2" --saida coletados.json
# escreva conteudo.json no formato de exemplo.json
python3 montar.py --coletados coletados.json --conteudo conteudo.json --saida boletim.html
node pdf.js boletim.html boletim.pdf
python3 votos.py --coletados coletados.json --saida votos.html && node pdf.js votos.html votos.pdf
```

O `pdf.js` usa o Playwright, já instalado nas sessões em nuvem.

### Câmaras das capitais

O levantamento de 27/10/2026 testou as 26 câmaras de capitais e a Câmara Legislativa do DF.

- **Com dados no boletim:**
  - pela API do SAPL (o sistema do Interlegis): Rio Branco, Manaus, Fortaleza, João Pessoa, Natal, Porto Velho, Boa Vista e Palmas;
  - pelo serviço SPLegis da Câmara Municipal: São Paulo.
- **Sem dados:** as outras 18. A maioria recusa conexões vindas da nuvem ou não tem dados abertos. Salvador fica de fora porque o sistema legislativo só tem endereço numérico, que a rede do ambiente não permite liberar. O motivo de cada uma está em `SEM_COBERTURA`, em `capitais.py`.

Quando uma câmara passar a responder, acrescente-a em `CAPITAIS_SAPL` e libere o domínio na rede do ambiente. Se ela deixar de responder, mova-a para `SEM_COBERTURA`.

## Uso no claude.ai/code (nuvem)

1. Crie ou edite um ambiente em claude.ai/code (menu do ambiente na barra de título → **Edit**).
2. Cole o conteúdo de `setup.sh` no campo **Setup script**.
3. Configure a rede e as variáveis (abaixo).
4. Abra uma sessão nova com este repositório selecionado.

O script roda no início de cada sessão. O acervo é baixado em `~/leis`, fora da pasta do repositório. Ele fica só no contêiner temporário da sessão e é apagado quando a sessão termina. Nada dele é enviado para este repositório.

O download é raso e parcial: traz só as pastas `federal/` e `jurisprudencia/`, além dos arquivos da raiz (`constituicao.md`, `COBERTURA.md`, `PROGRESSO.md`). São cerca de 3 GB. Para incluir leis estaduais, atos de órgãos reguladores ou leis municipais, acrescente `estaduais`, `reguladores` ou `municipais` à linha `git sparse-checkout set` do script. O download fica maior.

Os servidores MCP do `.mcp.json` só são carregados quando a sessão começa. Se um deles não aparecer em `/mcp`, a IA usa as APIs públicas via `curl` indicadas no `CLAUDE.md`.

### Variáveis de ambiente

Cadastre-as em **Edit**, no campo de variáveis do ambiente, uma por linha e sem aspas. Elas só valem em sessões novas.

```
DATAJUD_API_KEY=chave_publica_da_wiki_do_datajud
PORTAL_TRANSPARENCIA_API_KEY=chave_do_portal_da_transparencia
```

- **DataJud:** use só a chave, sem a palavra `APIKey`. A chave pública está na wiki do DataJud (CNJ).
- **Portal da Transparência:** a chave é gratuita, em https://portaldatransparencia.gov.br/api-de-dados.

### Rede

Em **Edit → Network access**, escolha **Limited** (ou **Custom**, nas versões antigas do app), deixe marcado **Allow package managers** e cole os domínios abaixo em **Allowed domains**.

<details>
<summary>Domínios usados pelo assistente e pelo boletim</summary>

```
api.bcb.gov.br
olinda.bcb.gov.br
servicodados.ibge.gov.br
apisidra.ibge.gov.br
dadosabertos.camara.leg.br
www.camara.leg.br
legis.senado.leg.br
www12.senado.leg.br
www25.senado.leg.br
senado.sidneybissoli.com
api-publica.datajud.cnj.jus.br
normas.leg.br
www.planalto.gov.br
www.gov.br
api.portaldatransparencia.gov.br
dadosabertos.tse.jus.br
cdn.tse.jus.br
www.in.gov.br
portal.stf.jus.br
noticias.stf.jus.br
www.stf.jus.br
api.queridodiario.ok.org.br
agenciabrasil.ebc.com.br
www.al.ba.gov.br
www.cms.ba.gov.br
sapl.riobranco.ac.leg.br
sapl.manaus.am.leg.br
sapl.fortaleza.ce.leg.br
sapl.joaopessoa.pb.leg.br
sapl.natal.rn.leg.br
sapl.portovelho.ro.leg.br
sapl.boavista.rr.leg.br
sapl.palmas.to.leg.br
splegisws.saopaulo.sp.leg.br
fonts.googleapis.com
fonts.gstatic.com
github.com
```

Veículos de notícia, de linhas editoriais diferentes, para o boletim ler as reportagens inteiras:

```
g1.globo.com
oglobo.globo.com
www1.folha.uol.com.br
www.estadao.com.br
www.poder360.com.br
www.congressoemfoco.com.br
www.cnnbrasil.com.br
www.metropoles.com
www.gazetadopovo.com.br
revistaoeste.com
www.cartacapital.com.br
www.bahianoticias.com.br
atarde.com.br
www.correio24horas.com.br
```

</details>

Alguns sites recusam acessos automáticos por conta própria, mesmo liberados. No teste de 27/10/2026, isso aconteceu com o endereço antigo da API do IBGE (`servicodados`), o Querido Diário, o Poder360 e a Revista Oeste. Nesses casos, o boletim usa outra fonte ou os resumos da busca na web e registra o fato nos avisos.

### Permissão de push

Para o Claude conseguir dar commit e push neste repositório, instale o [Claude GitHub App](https://github.com/apps/claude/installations/select_target). Em **Repository access**, escolha **Only select repositories** e marque só este repositório. Se o GitHub ainda não estiver ligado ao claude.ai, conecte em https://claude.ai/connect-github.

## Uso local (Claude Code no computador)

```bash
git clone https://github.com/vfdeoliveira1/consultor-civico.git
cd consultor-civico
bash setup.sh        # baixa o acervo em ~/leis
claude
```

O `setup.sh` usa `apt-get` para instalar o `ripgrep`. No Mac, instale antes com `brew install ripgrep`. Para gerar os PDFs do boletim no computador, instale também o Playwright (`npm install playwright` e `npx playwright install chromium`).

Para a chave do DataJud (consulta de processos), adicione ao `~/.bashrc` ou `~/.zshrc`:

```bash
export DATAJUD_API_KEY="cole_a_chave_aqui"
```

Os comandos para adicionar outros servidores MCP (IBGE, Câmara) estão no fim do `CLAUDE.md`.

## Uso com outras IAs

O repositório também serve para outras ferramentas, com ajustes:

- **Agentes de código que rodam comandos** (Codex, Cursor, GitHub Copilot, Gemini CLI): o `setup.sh`, o acervo e os scripts do boletim funcionam igual. As instruções do `CLAUDE.md` valem para qualquer modelo, mas cada ferramenta procura outro nome de arquivo. Muitas leem `AGENTS.md`, e o Gemini CLI lê `GEMINI.md`. Basta copiar ou renomear o arquivo.
- **Servidores MCP:** o Cursor e o VS Code também aceitam MCP, mas leem a configuração de `.cursor/mcp.json` e `.vscode/mcp.json`. O conteúdo do `.mcp.json` pode ser copiado para lá.
- **IAs só de chat** (ChatGPT, Gemini ou Claude no navegador): não conseguem pesquisar 3 GB de arquivos. O que dá para fazer é colar as regras do `CLAUDE.md` como instrução e enviar o arquivo da lei específica como anexo.

## Limitações

- Os textos do acervo são conversões automáticas, e cerca de 17 mil arquivos vieram de PDF escaneado com OCR. Pode haver erros. O link oficial fica no campo `fonte:` do cabeçalho de cada arquivo.
- Algumas categorias do acervo estão incompletas (decretos, medidas provisórias, parte da jurisprudência, alguns estados). Consulte `COBERTURA.md` e `PROGRESSO.md` em `~/leis`.
- Projetos em tramitação, indicadores econômicos e notícias não estão no acervo e dependem de fontes externas consultadas na hora.
- Votações simbólicas e secretas não têm voto individual, então não aparecem na consulta de votos.
- Os servidores MCP citados são projetos da comunidade, não oficiais. Revise o código antes de instalar. Os votos do Senado no boletim dependem do servidor `senado-br`; se ele cair, essa parte sai vazia e o boletim avisa.

As respostas e o boletim são informativos e não substituem um advogado em casos concretos.
