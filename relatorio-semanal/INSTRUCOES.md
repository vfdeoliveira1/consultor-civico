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
| **Paulo Câmara** | **A confirmar.** O leitor o citou como deputado federal eleito, mas a imprensa baiana (A Tarde, 5/10/2026) noticiou Paulo Câmara (PL-BA) **reeleito deputado estadual**, para o 3º mandato na Assembleia Legislativa da Bahia. Não há registro de Paulo Câmara entre os 39 federais eleitos pela Bahia. O ex-governador de Pernambuco Paulo Câmara (PSB) preside o Banco do Nordeste e não foi candidato. | Confirme o cargo no resultado do TSE e diga o que encontrou no próprio card. Até o leitor corrigir, trate como deputado estadual da Bahia: atuação na Assembleia, projetos, votações e declarações. |

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
8. **Responda** com o link da página e os destaques em 3 linhas. Essa mensagem vira a notificação no celular do leitor.

Não faça commit nem push dos boletins no repositório.

## Seções e fontes

| Seção | O que entra | Fontes |
|---|---|---|
| **O que importa** (`destaques`) | 4 a 6 frases, uma por assunto, do mais ao menos importante. | Tudo abaixo. |
| **Economia** (`economia`) | Os indicadores e gráficos vêm do `coleta.py`. Você escreve a análise: o que mudou na semana, decisões do Copom, divulgações (IPCA, PIB, emprego), dados fiscais e o que esperar. | `coleta.py` (SGS e Focus), MCP `bcb-br`, busca na web para o contexto. IBGE: tente `apisidra.ibge.gov.br`; se falhar, use a série do Banco Central e diga isso. |
| **Congresso e leis** (`leis`, `congresso`) | Leis sancionadas ou promulgadas, vetos, medidas provisórias editadas ou que perdem validade, PECs e projetos importantes aprovados ou rejeitados em cada Casa. Para cada lei, diga o que muda e compare com o texto anterior no acervo (`~/leis`). | API da Câmara (as votações vêm do `coleta.py`), MCP `senado-br` (matérias, votações, vetos), `normas.leg.br`, Diário Oficial (`www.in.gov.br`), acervo local. |
| **Deputados acompanhados** (`deputados`) | Um card por deputado da tabela de configuração. | Câmara (API e site), TSE (`dadosabertos.tse.jus.br`), Câmara Municipal de Salvador, Assembleia da Bahia, busca na web. |
| **Em evidência** (`em_evidencia`) | Os 3 a 5 deputados mais comentados, com o critério usado. A tabela de cota parlamentar vem do `coleta.py`. | Busca na web, API da Câmara, `coleta.py`. |
| **Governo federal** (`executivo`) | Decretos e portarias relevantes, anúncios de programas, decisões de ministérios, transição de governo (até as posses de 2027). | Diário Oficial, busca na web, Portal da Transparência (com a chave `PORTAL_TRANSPARENCIA_API_KEY`, quando houver). |
| **Justiça** (`justica`) | Julgamentos do STF e do STJ com efeito geral: repercussão geral, ações de controle de constitucionalidade, súmulas novas. | `portal.stf.jus.br`, pasta `jurisprudencia/` do acervo, busca na web. DataJud só para processos específicos. |
| **Bahia e Salvador** (`bahia`) | No máximo 3 itens: o que tiver efeito sobre o leitor ou ligação com o governo federal. | Busca na web, Querido Diário (`api.queridodiario.ok.org.br`). |
| **Agenda** (`agenda`) | A pauta do plenário da Câmara vem do `coleta.py`. Acrescente Senado, Copom, divulgações do IBGE, julgamentos marcados no STF e prazos de MPs. | MCP `senado-br`, calendários do Banco Central e do IBGE, pauta do STF. |
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

- `destaques`: lista de `{texto, link}`. `link` é o id da seção (`economia`, `congresso`, `deputados`, `evidencia`, `governo-justica`, `bahia`, `agenda`, `tema`).
- `economia`: `{intro, analise, fatos: [item]}`. `analise` aceita parágrafos separados por linha em branco.
- `leis`, `executivo`, `justica`, `bahia`, `congresso.itens`, `em_evidencia.deputados`: listas de **item**.
- **item**: `{titulo, texto, status, data, casa, o_que_muda, lados: {a, b, rotulo_a, rotulo_b}, fontes: [{nome, url}]}`. Só `titulo` é obrigatório. `status` aceita: aprovada, sancionada, promulgada, rejeitada, vetada, veto parcial, em tramitação, editada, perde validade.
- `deputados`: lista de `{nome, partido, uf, cargo, status, chave_ceap, fatos: [{tipo, texto, fontes}], lados, sem_novidades}`. `chave_ceap` é o nome em minúsculas e sem acento, igual ao passado ao `coleta.py`; deixe vazio para quem não é deputado federal em exercício.
- `em_evidencia`: `{criterio, deputados: [item]}`.
- `agenda`: lista de `{data, evento, onde}`. A data pode ter hora (`2026-11-03T14:00`).
- `tema_da_semana`: `{titulo, texto, fontes}`.
- `avisos`: lista de textos sobre o que não foi possível consultar.
