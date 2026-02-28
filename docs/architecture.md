# Arquitetura — rpaquintoandar

## Visao Geral

O rpaquintoandar e um RPA (Robotic Process Automation) para coleta de imoveis a venda no QuintoAndar.
Segue **Clean Architecture** com interfaces baseadas em `Protocol`, separando regras de negocio da infraestrutura.

## Camadas

```
┌─────────────────────────────────────────────────────────────────┐
│                         __main__.py                             │
│                     (CLI + bootstrap)                           │
├─────────────────────────────────────────────────────────────────┤
│                           Works                                 │
│           FullCrawlWork / ResumeWork / TestWorks                │
│                  (orquestram pipelines)                         │
├─────────────────────────────────────────────────────────────────┤
│                        Application                              │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐  │
│  │  Pipeline   │  │   Steps    │  │       Use Cases          │  │
│  │  Runner     │  │  Search    │  │  SearchListings          │  │
│  │  Context    │  │  Extract   │  │  ExtractDetail           │  │
│  │  IStep      │  │  Export    │  │  SegmentedSearch         │  │
│  └────────────┘  └────────────┘  └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                          Domain                                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────┐  ┌────────────┐    │
│  │ Entities │  │ Value Objects│  │ Enums │  │ Interfaces │    │
│  │ Listing  │  │ Address      │  │       │  │ (Protocols)│    │
│  │ Exec Run │  │ Coordinates  │  │       │  │            │    │
│  │ Step Rec │  │ PriceInfo    │  │       │  │            │    │
│  └──────────┘  └──────────────┘  └───────┘  └────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                       Infrastructure                            │
│  ┌──────────┐  ┌─────────────┐  ┌────────┐  ┌──────────────┐  │
│  │ Browser  │  │ Persistence │  │  API   │  │   Config     │  │
│  │Playwright│  │  SQLite     │  │ Search │  │  YAML loader │  │
│  │ Manager  │  │  aiosqlite  │  │ Coords │  │              │  │
│  └──────────┘  └─────────────┘  └────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                         Shared                                  │
│              Container (DI) / Logging / Hashing                 │
└─────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados (full-crawl)

```
                    ┌──────────────────┐
                    │   CLI / Config   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   SearchStep     │
                    │                  │
                    │ Coordinates API  │──── 10.000 IDs em ~5s
                    │   ou SSR pages   │──── 12 listings/pagina
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   DB: listings   │
                    │  status=PENDING  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  ExtractStep     │
                    │                  │
                    │ Detail pages     │──── __NEXT_DATA__ JSON
                    │ ~18min / 1000    │──── enriquece cada listing
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   DB: listings   │
                    │ status=ENRICHED  │
                    │  (ou FAILED /    │
                    │   DUPLICATE)     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   ExportStep     │
                    │                  │
                    │ JSON / CSV       │
                    │ data/export/     │
                    └──────────────────┘
```

## Mapa de Diretorios

```
src/rpaquintoandar/
├── __main__.py                 # Entry point CLI (argparse)
├── domain/
│   ├── entities/               # Listing, ExecutionRun, StepRecord
│   ├── enums/                  # PropertyType, ProcessingStatus, FurnishedStatus, etc.
│   ├── interfaces/             # Protocols: IBrowserManager, IListingRepository, etc.
│   └── value_objects/          # Address, Coordinates, PriceInfo, ContentHash, etc.
├── application/
│   ├── dtos/                   # SearchResult, ExtractResult
│   ├── pipeline/               # PipelineRunner, PipelineContext, IStep, StepOptions
│   ├── steps/                  # SearchStep, ExtractStep, ExportStep
│   └── use_cases/              # SearchListings, ExtractDetail, SegmentedSearch
├── infrastructure/
│   ├── api/                    # QuintoAndarApiClient, CoordinatesCollector, ResponseParser
│   ├── browser/                # PlaywrightBrowserManager, DetailExtractor, PageObjects
│   ├── config/                 # Settings + YAML loader
│   └── persistence/            # DatabaseManager, SqliteListingRepo, SqliteExecutionRepo
├── shared/                     # Container (DI), logging, hashing
└── works/                      # FullCrawlWork, ResumeWork, TestWorks
```

## Entidades Principais

### Listing (39 campos)

Representa um imovel. Ciclo de vida:

```
PENDING ──enrich──► ENRICHED ──export──► arquivo JSON/CSV
    │
    ├──hash match──► DUPLICATE
    └──erro────────► FAILED
```

### ExecutionRun

Registro de cada execucao do pipeline. Possui `mode` (full-crawl, resume, test-search, test-listing) e `status`.

### StepRecord

Registro de cada step dentro de um run. Armazena contadores (`items_processed`, `items_created`, `items_failed`) e erros.

## Banco de Dados

SQLite com `aiosqlite` e WAL mode. Tres tabelas:

| Tabela           | Chave          | Descricao                        |
|------------------|----------------|----------------------------------|
| `listings`       | `source_id` UQ | Imoveis coletados                |
| `execution_runs` | `id` PK        | Registro de execucoes            |
| `step_records`   | `id` PK (FK)   | Steps dentro de cada execucao    |

Migracoes automaticas via `DatabaseManager.initialize()`.

## Modos de Execucao

| Modo            | Steps                      | Descricao                              |
|-----------------|-----------------------------|----------------------------------------|
| `full-crawl`   | Search → Extract → Export   | Pipeline completo                      |
| `resume`        | Extract → Export            | Retoma enriquecimento de pendentes     |
| `test-search`   | Search (1 pagina)          | Testa busca de uma pagina              |
| `test-listing`  | Extract (1 listing)        | Testa extracao de um imovel especifico |

## Dependencias

| Pacote       | Uso                                    |
|-------------|----------------------------------------|
| `playwright` | Automacao de browser (Chromium)        |
| `aiosqlite`  | Acesso async ao SQLite                 |
| `pyyaml`     | Carregamento de configuracao           |
| `httpx`      | Cliente HTTP async (coordinates API)   |
