#!/bin/bash
# Script de setup do ambiente em claude.ai/code
# Cole este conteúdo no campo "Setup script" do ambiente.
set -e

# ripgrep (busca no acervo)
command -v rg >/dev/null || (apt-get update -qq && apt-get install -y -qq ripgrep)

# Acervo de leis: clone raso e parcial, só as pastas usadas
if [ ! -d "$HOME/leis" ]; then
  git clone --depth 1 --filter=blob:none --sparse https://github.com/ctresb/leis.git "$HOME/leis"
  cd "$HOME/leis"
  git sparse-checkout set federal jurisprudencia tratados
fi

# Pré-baixa o MCP do Banco Central para a sessão iniciar mais rápido
npm install -g bcb-br-mcp >/dev/null 2>&1 || true
