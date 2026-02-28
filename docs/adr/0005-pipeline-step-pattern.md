# ADR-0005: Pipeline com Steps Sequenciais

- **Status:** Aceita
- **Data:** 2025-02-01
- **Decisores:** DevViking-Persike

## Contexto e Problema

O processo de coleta de imoveis tem fases distintas:
1. **Busca**: Coletar IDs de imoveis (via coordinates API ou SSR).
2. **Extracao**: Enriquecer cada listing com dados da pagina de detalhe.
3. **Exportacao**: Gerar arquivos JSON/CSV com os dados enriquecidos.

Cada fase pode falhar independentemente, tem duracao diferente (~5s busca, ~18min extracao, ~1s exportacao) e precisa de metricas proprias.

## Decisao

Implementar um **Pipeline com Steps sequenciais**:

```
PipelineRunner
├── SearchStep      →  StepResult (total_found, new_listings)
├── ExtractStep     →  StepResult (processed, enriched, failed)
└── ExportStep      →  StepResult (items_exported)
```

### Componentes

- **`IStep` (Protocol)**: Interface com `name: str` e `execute(context) → StepResult`.
- **`PipelineRunner`**: Orquestra steps em sequencia. Cria `ExecutionRun` e `StepRecord` no banco.
- **`PipelineContext`**: Container de estado compartilhado entre steps (DI container, criteria, listings, results).
- **`StepResult`**: Value object com status, contadores e lista de erros.
- **`StepOptions`**: Configuracoes como `continue_on_error` e `max_retries`.

### Composicao por Work

Diferentes modos compoem pipelines diferentes:
- `FullCrawlWork`: Search → Extract → Export
- `ResumeWork`: Extract → Export (pula busca)
- Test works: steps individuais

## Alternativas Consideradas

### Funcoes sequenciais (procedural)
- **Pros:** Simples, sem abstraccoes.
- **Contras:** Sem rastreabilidade, sem metricas por fase, dificil adicionar/remover etapas.

### Task queue (Celery/RQ)
- **Pros:** Paralelismo, retry automatico, distribuido.
- **Contras:** Overhead enorme para uso local. Requer broker (Redis/RabbitMQ).

### DAG-based (Airflow/Prefect)
- **Pros:** Visualizacao, scheduling, retry granular.
- **Contras:** Infra pesada, overengineering para 3 steps sequenciais.

## Consequencias

### Positivas
- **Extensivel**: Adicionar um step (ex: `NotifyStep`, `ValidateStep`) requer apenas implementar `IStep`.
- **Resumivel**: `ResumeWork` pula a busca e retoma do `ExtractStep`, aproveitando listings pendentes no banco.
- **Rastreavel**: Cada execucao gera registros em `execution_runs` e `step_records` com contadores e timestamps.
- **Testavel**: Steps podem ser testados isoladamente com contexto mockado.

### Negativas
- **Sequencial**: Steps rodam um por vez. Se paralelismo for necessario no futuro, o `PipelineRunner` precisara ser refatorado.
- **Acoplamento ao contexto**: Steps compartilham estado via `PipelineContext`, o que pode gerar dependencias implicitas entre steps.
