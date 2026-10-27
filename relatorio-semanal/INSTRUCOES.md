# Boletim Cívico semanal

Instruções para a sessão que monta o boletim toda segunda-feira. Siga também as regras do `CLAUDE.md` da raiz: nada de memória, todo número vem de consulta feita na sessão, toda afirmação tem fonte.

Para mudar o boletim, edite este arquivo. A tarefa agendada só manda ler e seguir o que está aqui.

## Configuração

- **Leitor:** mora em Salvador (BA). Prioridade para o governo federal e o Congresso. Bahia e Salvador entram só em um resumo curto.
- **Período:** a semana anterior, de segunda a domingo. O `coleta.py` calcula sozinho.
- **Formato:** página publicada no claude.ai, com tabelas e gráficos, relatório completo.

### Deputados acompanhados

| Nome | Situação conhecida | O que acompanhar |
|---|---|---|
| **Sandro Filho** (PP-BA) | Eleito deputado federal em 4/10/2026, o mais jovem da história da Bahia. Toma posse na Câmara em 1º/02/2027. Até lá é vereador de Salvador. | Transição e articulação para o mandato (bancada, partido, comissões pretendidas), prestação de contas da campanha no TSE, atuação na Câmara Municipal de Salvador, declarações públicas relevantes. Depois da posse, incluir o nome em `--deputados` no `coleta.py`. |
| **Paulo Câmara** (PL-BA) | Deputado estadual da Bahia, reeleito em 4/10/2026 para o 3º mandato na Assembleia Legislativa da Bahia (Alba). Confirmado pelo leitor. Não confundir com o ex-governador de Pernambuco Paulo Câmara (PSB), que preside o Banco do Nordeste. | Atuação na Assembleia (projetos, votações, comissões, discursos), declarações públicas relevantes e posições sobre temas federais. Fontes: site da Alba (`www.al.ba.gov.br`), imprensa baiana, busca na web. A cota parlamentar federal não se aplica. |

Quando o leitor mudar esta lista, siga a versão nova.

### Deputados em evidência

Além dos acompanhados, escolha de **3 a 5 deputados federais em exercício** que foram os mais comentados da semana. Não há API de redes sociais. Use este método e explique-o em `em_evidencia.criterio`:

1. Faça buscas na web pela semana: "deputado federal" com termos como polêmica, viraliza, redes sociais, discurso, Conselho de Ética, aprovado, relator.
2. Fique com quem aparece em **várias reportagens de veículos de linhas editoriais diferentes**. Uma única reportagem não basta.
3. Equilibre o espectro político: não escolha só deputados de um lado.
4. Para cada um, registre o que fez, com fonte, e como cada lado avaliou.

Passe esses nomes também ao `coleta.py` (`--deputados`), para trazer votos e cota parlamentar.

## Passo a passo

1. **Prepare o ambiente.** Rode `cd ~/leis` e confirme que o acervo existe. Se não existir, rode `bash setup.sh` na raiz do repositório.
2. **Pesquise a semana** (seções abaixo) e anote os fatos com as fontes. Escolha os deputados em evidência.
3. **Colete os dados estruturados:**
   ```bash
   cd relatorio-semanal
   python3 coleta.py --deputados "Nome 1,Nome 2,Nome 3" --saida /tmp/boletim/coletados.json
   ```
   Use o nome parlamentar como aparece no site da Câmara. Leia os avisos que o script imprimir e repita no rodapé o que falhou.
4. **Escreva o conteúdo** em `/tmp/boletim/conteudo.json`, no formato de `exemplo.json`. O formato está descrito em "Formato do conteúdo".
5. **Monte a página:**
   ```bash
   python3 montar.py --coletados /tmp/boletim/coletados.json --conteudo /tmp/boletim/conteudo.json --saida /tmp/boletim/boletim-AAAA-MM-DD.html
   ```
6. **Confira a página uma vez** com o Playwright pré-instalado: abra o HTML, veja se não há erro no console e se as seções aparecem. Não altere o `modelo.html` na sessão semanal. Se algo estiver quebrado, conserte o `conteudo.json`.
7. **Publique.** Carregue o skill `artifact-design` (a ferramenta exige) e publique o HTML com a ferramenta Artifact, como página nova, com `icon: "news"` e uma `description` de uma frase com os 2 ou 3 assuntos principais. Não reescreva o design: o modelo já segue o contrato da página.
8. **Registre a edição no arquivo.** O arquivo de edições é a página https://claude.ai/artifact/XQdiMS4ZgKSMxFEKSv8Q5U, que lê um banco de dados próprio. Com a ferramenta `ArtifactData`, grave um documento na coleção `edicoes` com `doc_id` igual à data de início da semana (`AAAA-MM-DD`):
   ```json
   {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD", "edicao": "semana ISO/ano, como no cabeçalho do boletim", "publicado_em": "AAAA-MM-DD",
    "titulo": "título da página", "url": "link da página publicada", "teste": false,
    "votacoes_nominais": 0, "destaques": ["os 3 primeiros destaques, uma frase cada"]}
   ```
   `votacoes_nominais` é a soma das votações nominais da Câmara e do Senado no `coletados.json`. Se já existir documento com esse `doc_id` (uma edição refeita), leia-o com `get` e grave com `if_version`. Não republique a página do arquivo.
9. **Gere o PDF** do mesmo HTML:
   ```bash
   node pdf.js /tmp/boletim/boletim-AAAA-MM-DD.html /tmp/boletim/boletim-AAAA-MM-DD.pdf
   ```
   O script imprime o tamanho e o número de seções. Se ele sair com erro, conserte o `conteudo.json` e gere de novo.
   Gere também o PDF separado **Votos da semana**, com o voto de cada deputado e senador:
   ```bash
   python3 votos.py --coletados /tmp/boletim/coletados.json --saida /tmp/boletim/votos-AAAA-MM-DD.html
   node pdf.js /tmp/boletim/votos-AAAA-MM-DD.html /tmp/boletim/votos-AAAA-MM-DD.pdf
   ```
   Se o `votos.py` sair com código 3, a semana não teve votação nominal: não há PDF de votos, e isso vai na resposta final.
10. **Envie os PDFs** ao leitor com a ferramenta `SendUserFile` (`status: "proactive"`, `display: "attach"`), numa única chamada com os dois arquivos e a legenda "Boletim Cívico e votos da semana, DD/MM a DD/MM". Se a ferramenta não estiver disponível, diga isso na resposta final.
11. **Responda** com o link da página, o aviso de quais PDFs foram enviados e os destaques em 3 linhas. Essa mensagem vira a notificação no celular do leitor.

Não faça commit nem push dos boletins nem dos PDFs no repositório.

## Seções e fontes

| Seção | O que entra | Fontes |
|---|---|---|
| **O que importa** (`destaques`) | 4 a 6 frases, uma por assunto, do mais ao menos importante. | Tudo abaixo. |
| **Economia** (`economia`) | Os indicadores e gráficos vêm do `coleta.py`. Você escreve a análise: o que mudou na semana, decisões do Copom, divulgações (IPCA, PIB, emprego), dados fiscais e o que esperar. | `coleta.py` (SGS e Focus), MCP `bcb-br`, busca na web para o contexto. IBGE: tente `apisidra.ibge.gov.br`; se falhar, use a série do Banco Central e diga isso. |
| **Congresso e leis** (`leis`, `congresso`) | PECs e projetos importantes aprovados ou rejeitados em cada Casa, leis promulgadas pelo Congresso e vetos derrubados ou mantidos. Para cada lei, diga o que muda e compare com o texto anterior no acervo (`~/leis`). As votações dos plenários da Câmara e do Senado, com o voto de cada parlamentar, entram sozinhas pelo `coleta.py`: não as repita. Use o `conteudo.json` para explicar as votações mais importantes. | API da Câmara e MCP `senado-br` (já chamados pelo `coleta.py`), `normas.leg.br`, Diário Oficial (`www.in.gov.br`), acervo local. |
| **Consultar um parlamentar** | Seção automática: busca por nome de qualquer deputado federal ou senador em exercício, com os votos nas votações nominais, os discursos, as proposições apresentadas e a cota parlamentar da semana. Não precisa de conteúdo. | `coleta.py` e `atividade.py`. |
| **Deputados acompanhados** (`deputados`) | Um card por deputado da tabela de configuração. | Câmara (API e site), TSE (`dadosabertos.tse.jus.br`), Câmara Municipal de Salvador, Assembleia da Bahia, busca na web. |
| **Em evidência** (`em_evidencia`) | Os 3 a 5 deputados mais comentados, com o critério usado. A tabela de cota parlamentar vem do `coleta.py`. | Busca na web, API da Câmara, `coleta.py`. |
| **Presidente e governo federal** (`presidente`) | O que o Presidente da República fez na semana, em grupos: `sancoes` (leis sancionadas), `vetos` (vetos novos, totais ou parciais), `mps` (medidas provisórias editadas ou que perderam validade), `decretos` (decretos e outros atos relevantes) e `agenda` (agenda oficial, viagens, anúncios de programas, transição até as posses de 2027). A tabela de vetos à espera do Congresso vem do `coleta.py`. | Diário Oficial, agenda do Presidente em `www.gov.br/planalto`, MCP `senado-br` (vetos), busca na web, Portal da Transparência (com a chave `PORTAL_TRANSPARENCIA_API_KEY`, quando houver). |
| **Justiça** (`justica`) | Julgamentos do STF e do STJ com efeito geral: repercussão geral, ações de controle de constitucionalidade, súmulas novas. | `portal.stf.jus.br`, pasta `jurisprudencia/` do acervo, busca na web. DataJud só para processos específicos. |
| **Câmaras das capitais** | Seção automática: projetos de lei e leis publicadas na semana nas câmaras das capitais com dados abertos (lista em `capitais.py`), com busca por vereador. Não precisa de conteúdo. Se uma câmara do levantamento passar a responder, ou deixar de responder, atualize `CAPITAIS_SAPL` e `SEM_COBERTURA` em `capitais.py`. | `coleta.py` e `capitais.py`. |
| **Bahia e Salvador** (`bahia`) | No máximo 3 itens: o que tiver efeito sobre o leitor ou ligação com o governo federal. | Busca na web, Querido Diário (`api.queridodiario.ok.org.br`). |
| **Agenda** (`agenda`) | A pauta do plenário da Câmara vem do `coleta.py` e entra sozinha: não a repita no `conteudo.json`. Acrescente Senado, Copom, divulgações do IBGE, julgamentos marcados no STF e prazos de MPs. | MCP `senado-br`, calendários do Banco Central e do IBGE, pauta do STF. |
| **Para entender** (`tema_da_semana`) | 3 a 5 parágrafos didáticos sobre o assunto mais discutido: o que é, o que diz a lei (com artigo e arquivo do acervo), quais são os argumentos. | Acervo local e as fontes da semana. |

## Regras de redação

- Português claro, frases curtas, sem jargão. Explique siglas na primeira vez.
- Separe fato de interpretação. O que é opinião fica em `lados`, sempre com os dois lados, cada um descrito como seus defensores o descreveriam.
- Não use adjetivos de julgamento ("absurdo", "histórico", "vergonhoso") fora de citações atribuídas.
- **Selos dos fatos de deputados:**
  - `entrega`: fato concreto do mandato, como projeto aprovado, relatoria concluída ou presença em votação importante.
  - `atencao`: fato verificável que merece olhar crítico, como falta em votação, gasto acima da média, voto contra a orientação do próprio partido ou investigação aberta.
  - `registro`: fato sem juízo, como uma declaração, uma reunião ou uma filiação.
- Gasto alto na cota não é irregularidade. Diga que a cota varia por estado.
- Toda afirmação tem pelo menos uma fonte com link. Notícia de um só veículo vira "segundo o veículo X".
- Datas no formato dd/mm/aaaa e valores em R$ com separador brasileiro.
- Se uma fonte falhar ou uma seção ficar sem fatos, diga isso em `avisos`. Não preencha com suposições.
- Busca na web pode trazer data errada ou notícia antiga. Confira a data de cada reportagem e confirme os fatos nas fontes oficiais quando possível.

## Formato do conteúdo

`conteudo.json` segue `exemplo.json`. Campos:

- `destaques`: lista de `{texto, link}`. `link` é o id da seção (`economia`, `congresso`, `parlamentares`, `deputados`, `evidencia`, `presidente`, `justica`, `capitais`, `bahia`, `agenda`, `tema`).
- `economia`: `{intro, analise, fatos: [item]}`. `analise` aceita parágrafos separados por linha em branco.
- `presidente`: `{intro, sancoes, vetos, mps, decretos, agenda}`, cada grupo uma lista de **item**. O campo antigo `executivo` ainda funciona e aparece como "Outros atos do governo".
- `leis`, `justica`, `bahia`, `congresso.itens`, `em_evidencia.deputados`: listas de **item**.
- **item**: `{titulo, texto, status, data, casa, o_que_muda, lados: {a, b, rotulo_a, rotulo_b}, fontes: [{nome, url}]}`. Só `titulo` é obrigatório. `status` aceita: aprovada, sancionada, promulgada, rejeitada, vetada, veto parcial, em tramitação, editada, perde validade.
- `deputados`: lista de `{nome, partido, uf, cargo, status, chave_ceap, fatos: [{tipo, texto, fontes}], lados, sem_novidades}`. `chave_ceap` é o nome em minúsculas e sem acento, igual ao passado ao `coleta.py`; deixe vazio para quem não é deputado federal em exercício.
- `em_evidencia`: `{criterio, deputados: [item]}`.
- `agenda`: lista de `{data, evento, onde}`. A data pode ter hora (`2026-11-03T14:00`).
- `tema_da_semana`: `{titulo, texto, fontes}`.
- `avisos`: lista de textos sobre o que não foi possível consultar.
