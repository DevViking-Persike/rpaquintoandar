# ADR-0004: SQLite com aiosqlite e WAL Mode

- **Status:** Aceita
- **Data:** 2025-02-01
- **Decisores:** DevViking-Persike

## Contexto e Problema

O sistema precisa persistir listings coletados entre execucoes para suportar:
- **Resume mode**: Retomar enriquecimento de listings pendentes sem reexecutar a busca.
- **Deduplicacao**: Evitar processar o mesmo imovel duas vezes via `content_hash`.
- **Rastreabilidade**: Registrar execucoes (`execution_runs`) e steps (`step_records`) com contadores.

## Decisao

Usar **SQLite** via **aiosqlite** (wrapper async) com:

- **WAL mode** (Write-Ahead Logging) para permitir leituras concorrentes durante escrita.
- **Upsert** em `source_id` (UNIQUE) para deduplicacao automatica.
- **Migracoes automaticas** via `DatabaseManager.initialize()` com tabela `schema_version`.
- **Foreign keys** habilitadas para integridade referencial (`step_records` → `execution_runs`).

### Schema

```
listings (30+ colunas)
├── source_id TEXT UNIQUE      # ID do imovel no QuintoAndar
├── status TEXT                # PENDING → ENRICHED | FAILED | DUPLICATE
├── content_hash TEXT          # SHA256 para deduplicacao
└── indices em status, source_id, content_hash, neighborhood, city, sale_price

execution_runs
├── mode TEXT                  # full-crawl, resume, test-search, test-listing
└── status TEXT                # running → succeeded | failed

step_records (FK execution_run_id)
├── step_name TEXT             # search, extract, export
└── contadores: items_processed, items_created, items_failed
```

## Alternativas Consideradas

### PostgreSQL
- **Pros:** Robusto, suporta concorrencia pesada, tipos avancados.
- **Contras:** Requer servidor externo, configuracao, docker-compose. Overhead desnecessario para uso local.

### JSON files
- **Pros:** Zero dependencia, legivel.
- **Contras:** Sem queries, sem transacoes, sem deduplicacao eficiente. Nao escala para 10.000+ listings.

### TinyDB / shelve
- **Pros:** Simples, Python puro.
- **Contras:** Sem SQL, sem indices, performance ruim em volume.

## Consequencias

### Positivas
- **Zero configuracao**: Arquivo unico em `data/rpaquintoandar.db`, sem servidor.
- **Portavel**: Banco pode ser copiado, versionado ou inspecionado com `sqlite3` CLI.
- **Async nativo**: `aiosqlite` integra naturalmente com o loop asyncio do Playwright.
- **Resume mode**: Basta filtrar `status = 'pending'` para retomar de onde parou.

### Negativas
- **Escrita serializada**: SQLite so permite um writer por vez (WAL ameniza mas nao elimina).
- **Sem tipos ricos**: Listas e dicts sao serializados como JSON strings nas colunas TEXT.
- **Migracao manual**: Schema changes requerem adicionar novas funcoes de migracao no `DatabaseManager`.
