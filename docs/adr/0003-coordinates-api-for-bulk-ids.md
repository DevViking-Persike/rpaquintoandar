# ADR-0003: Coordinates API para Coleta em Massa de IDs

- **Status:** Aceita
- **Data:** 2025-02-01
- **Decisores:** DevViking-Persike

## Contexto e Problema

A busca SSR do QuintoAndar retorna no maximo ~12 listings por pagina. Para coletar 1.000+ imoveis, seriam necessarias ~84 paginas, cada uma carregada via Playwright (~1s cada). Alem disso, a paginacao SSR tende a ciclar os mesmos resultados apos algumas paginas.

Observamos que o front-end do QuintoAndar faz uma chamada interna a API `search/coordinates` que retorna **ate 10.000 IDs com coordenadas** em uma unica request.

## Decisao

Implementar o `CoordinatesCollector` que:

1. Carrega uma pagina de busca via Playwright para capturar a URL e headers da request `search/coordinates`.
2. Replica essa request via `httpx` (async HTTP client) para obter a lista completa de IDs.
3. Cria listings minimos (source_id + coordenadas) com status `PENDING` no banco.
4. O `ExtractStep` subsequente enriquece cada listing individualmente.

Essa abordagem e ativada quando `target_count > 0` no CLI (`--target N`), via `SegmentedSearchUseCase`.

## Alternativas Consideradas

### Paginacao SSR completa
- **Pros:** Simples, sem interceptacao de APIs internas.
- **Contras:** Lento (~84s para 1000 IDs), ciclagem de resultados, limite pratico de ~200-300 IDs unicos.

### API publica do QuintoAndar
- **Pros:** Estavel, documentada.
- **Contras:** Nao existe API publica para busca de imoveis a venda.

## Consequencias

### Positivas
- **Velocidade**: Coleta de 1.000+ IDs em ~5 segundos (1 page load + 1 HTTP request).
- **Completude**: Retorna todos os imoveis disponiveis na regiao, sem ciclagem.
- **Coordenadas inclusas**: Cada ID ja vem com latitude/longitude, util para filtros geograficos.

### Negativas
- **Fragilidade**: Depende de API interna nao documentada. Mudancas no front-end podem quebrar a interceptacao.
- **Dados minimos**: So retorna ID e coordenadas. Enriquecimento completo ainda depende de carregar cada pagina de detalhe (~18min/1000).
- **Segmentacao por preco**: Para contornar limites de resultados, a busca e segmentada por faixas de preco (configuravel em `settings.yaml`).
