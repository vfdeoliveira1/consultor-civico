#!/usr/bin/env node
// Gera o PDF do boletim a partir do HTML montado pelo montar.py (ou baixado da página publicada).
//
// Uso:
//   node pdf.js boletim.html boletim.pdf
//
// Usa o Playwright pré-instalado no ambiente. O PDF sai em A4, sempre no tema claro,
// com número de página no rodapé. Os estilos de impressão ficam aqui, e não no
// modelo.html, para valer também em páginas publicadas antes deles.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const IMPRESSAO = `
  @page { size: A4; margin: 16mm 14mm 18mm; }
  body { background: #fff !important; padding: 0 !important; font-size: 10.5pt !important; }
  .coluna { max-width: none !important; gap: 1.6rem !important; }
  .cabecalho { padding-block: 0 1rem !important; }
  .cabecalho h1 { font-size: 26pt !important; }
  /* Na página cada tópico abre sozinho; no PDF saem todos, e os botões do fim de cada tópico somem. */
  section.inativa { display: flex !important; }
  .topicos-fim, .voltar { display: none !important; }
  .inicio .intro { display: none !important; }
  section { gap: .8rem !important; break-before: auto; }
  .secao-topo { break-after: avoid; }
  h2, h3 { break-after: avoid; }
  .ind, .grafico, .deputado .topo, .item, .lados > div, .tema, tr, .barra, .destaques li { break-inside: avoid; }
  .indicadores { grid-template-columns: repeat(3, 1fr) !important; }
  .tabela { overflow: visible !important; }
  table { font-size: 9pt !important; }
  th { white-space: normal !important; }
  a { color: inherit !important; text-decoration-color: #9bb; }
  /* Busca e votos individuais só existem na página online; no PDF ficam o placar e a orientação. */
  #como-votou .intro, #como-votou .busca, #como-votou .resultados, details.votos { display: none !important; }
  .so-impressao { display: block !important; }
  /* No PDF cada capital fica numa linha de resumo; a lista de projetos e a busca ficam na página. */
  #capitais .busca, #capitais .resultados { display: none !important; }
  details.capital { padding: .3rem .6rem !important; break-inside: avoid; }
  .votacao { break-inside: avoid; }
`;

async function main() {
  const [entrada, saida] = process.argv.slice(2);
  if (!entrada || !saida) {
    console.error("uso: node pdf.js boletim.html boletim.pdf");
    process.exit(2);
  }
  let html = fs.readFileSync(entrada, "utf8");
  // O HTML do montar.py é um fragmento: a página publicada recebe o esqueleto na hora de publicar.
  if (!/^\s*<!doctype/i.test(html)) {
    html = `<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${html}</body></html>`;
  }
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "boletim-")), "pagina.html");
  fs.writeFileSync(tmp, html);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 } });
  const erros = [];
  page.on("pageerror", (e) => erros.push(String(e)));
  await page.emulateMedia({ media: "print", colorScheme: "light" });
  await page.goto("file://" + tmp, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.addStyleTag({ content: `@media print { ${IMPRESSAO} }` });
  const secoes = await page.evaluate(() => document.querySelectorAll("section").length);
  const titulo = await page.title();
  await page.pdf({
    path: saida,
    format: "A4",
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: "<span></span>",
    footerTemplate: `<div style="width:100%;font:8px Arial,sans-serif;color:#667;padding:0 14mm;display:flex;justify-content:space-between"><span>${titulo.replace(/</g, "&lt;")}</span><span><span class="pageNumber"></span> de <span class="totalPages"></span></span></div>`,
    preferCSSPageSize: true,
  });
  await browser.close();
  const kb = Math.round(fs.statSync(saida).size / 1024);
  console.log(`${saida}: ${kb} KB, ${secoes} seções${erros.length ? ", erros: " + erros.join("; ") : ""}`);
  if (!secoes || erros.length) process.exit(1);
}

main().catch((e) => { console.error(e); process.exit(1); });
