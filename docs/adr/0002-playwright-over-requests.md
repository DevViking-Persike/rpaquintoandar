# ADR-0002: Playwright para Navegacao em vez de Requests

- **Status:** Aceita
- **Data:** 2025-02-01
- **Decisores:** DevViking-Persike

## Contexto e Problema

O QuintoAndar usa Next.js com Server-Side Rendering (SSR). Os dados dos imoveis ficam em um blob JSON dentro de `<script id="__NEXT_DATA__">`. Alem disso, o site e protegido por WAF (CloudFront) que bloqueia requests diretos sem cookies/headers de sessao validos.

Precisamos de uma forma confiavel de:
1. Carregar paginas de busca para coletar IDs de imoveis.
2. Carregar paginas de detalhe para extrair dados enriquecidos do `__NEXT_DATA__`.

## Decisao

Usar **Playwright** (Chromium headless) como engine de navegacao.

A arquitetura encapsula o Playwright atras de interfaces:
- `IBrowserManager` — ciclo de vida do browser (start/stop/new_page).
- `IDetailExtractor` — extrai `__NEXT_DATA__` de paginas de detalhe.
- Page Objects (`BasePage`, `ListingDetailPage`) — encapsulam interacoes com paginas.

## Alternativas Consideradas

### requests / httpx direto
- **Pros:** Muito mais rapido, sem overhead de browser.
- **Contras:** Bloqueado pelo WAF/CloudFront. Requer engenharia reversa de cookies, headers e tokens que mudam frequentemente.

### Selenium
- **Pros:** Maduro, ampla documentacao.
- **Contras:** Mais lento que Playwright, API menos ergonomica para async, maior consumo de memoria.

### Scrapy + Splash
- **Pros:** Framework robusto para scraping em larga escala.
- **Contras:** Splash adiciona complexidade de deploy (container Docker), menos controle fino sobre interacoes de pagina.

## Consequencias

### Positivas
- **Confiabilidade**: Navega como um browser real, contorna protecoes WAF sem engenharia reversa.
- **Interceptacao de APIs**: Permite capturar requests internos do browser (ex: coordinates API) via `page.route()`.
- **`__NEXT_DATA__` acessivel**: Executa JavaScript na pagina para extrair o blob JSON diretamente.

### Negativas
- **Velocidade**: ~1s por pagina de detalhe vs ~100ms com requests direto. ~18 minutos para 1000 listings.
- **Recursos**: Chromium headless consome ~200-400MB de RAM.
- **Dependencia binaria**: Requer instalacao do Chromium via `playwright install chromium`.
