# ADR-0001: Clean Architecture com Protocol-based Interfaces

- **Status:** Aceita
- **Data:** 2025-02-01
- **Decisores:** DevViking-Persike

## Contexto e Problema

O rpaquintoandar precisa coletar dados de imoveis do QuintoAndar, que envolve automacao de browser, persistencia em banco, parsing de APIs e exportacao de dados. Sem separacao de camadas, o codigo de infra (Playwright, SQLite) ficaria acoplado a logica de negocio, dificultando testes e manutencao.

## Decisao

Adotar **Clean Architecture** com quatro camadas:

1. **Domain** — Entidades (`Listing`, `ExecutionRun`, `StepRecord`), value objects (`Address`, `Coordinates`, `PriceInfo`), enums e interfaces (Protocols).
2. **Application** — Use cases (`SearchListings`, `ExtractDetail`, `SegmentedSearch`), pipeline (`PipelineRunner`, `IStep`), steps e DTOs.
3. **Infrastructure** — Implementacoes concretas: Playwright, SQLite, API clients, config loader.
4. **Shared** — Container de DI, logging, utilitarios.

Interfaces sao definidas como `typing.Protocol` no dominio. Implementacoes concretas na infra satisfazem esses protocolos sem heranca explicita (structural subtyping).

## Alternativas Consideradas

### Script monolitico
- **Pros:** Rapido de implementar, sem boilerplate.
- **Contras:** Impossivel de testar unitariamente, dificil de manter.

### Hexagonal Architecture (Ports & Adapters)
- **Pros:** Similar em separacao, bem documentada.
- **Contras:** Terminologia menos intuitiva para o contexto; Clean Architecture comunica melhor a direcao de dependencia.

## Consequencias

### Positivas
- **Testabilidade**: Use cases testados com mocks, sem precisar de browser ou banco real.
- **Substituibilidade**: Trocar SQLite por Postgres ou Playwright por outro browser requer apenas nova implementacao da interface.
- **Clareza**: Cada arquivo tem responsabilidade unica e camada bem definida.

### Negativas
- **Mais arquivos**: ~50 arquivos em vez de um script simples.
- **Overhead conceitual**: Requer compreensao de protocolos, DI e camadas para contribuir.

## Links

- [The Clean Architecture — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [PEP 544 — Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
