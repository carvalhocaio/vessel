# vessel

Pipeline de dados do perfil @1caiocarvalho (Fórmula 1, temporada 2027). Calcula números e gráficos e gera `draft.json` para um agente curador (Google ADK) escrever rascunhos para o X. O pipeline calcula; o agente só escreve. Nenhum número nasce no agente.

Arquitetura e roadmap: https://claude.ai/artifact/AbT4TyibVtaKRcU4z9JxAn

## Como trabalhar

- Converse comigo em português do Brasil; código, nomes, mensagens de commit e logs em inglês.
- Antes de implementar uma etapa, apresente o plano (arquivos, contratos, testes) e espere minha aprovação.
- Não faça commit, push nem crie branch. Ao final de cada etapa, entregue a mensagem de commit (Conventional Commits, em inglês).
- Comandos de terminal para o shell fish.
- Antes de dizer que terminou, rode e deixe passando:
  `uv run ruff format .; and uv run ruff check .; and uv run mypy src tests; and uv run pytest`
- Gerou gráfico? Abra o PNG e confira layout (sobreposição de texto, rodapé, legibilidade no celular) antes de concluir.

## Regras de código

- Python 3.13, uv, PEP 8, SOLID, DRY, mypy strict.
- Sem docstrings nem comentários longos; o código deve se explicar pelos nomes.
- Modelos de domínio em pydantic v2, `frozen=True, extra="forbid"`, datetimes sempre com fuso (UTC no domínio, America/Cuiaba só na apresentação).
- Fontes ficam atrás de `Protocol` em `src/vessel/sources/ports.py` (regra do "fornecedor de pneu": trocar a fonte não muda o carro).
- Funções de análise são puras sobre DataFrame, em `src/vessel/analytics/`, testáveis sem rede.
- Testes nunca acessam a rede: use fixtures gravadas de dados reais em `tests/fixtures/` e fakes que implementam os Protocols. Factories em `tests/factories.py`.
- Números exibidos em pt-BR via `vessel.formatting.format_decimal`.

## Peças que já existem

- `domain/`: `Event`, `Session`, `SessionKind`, `EventFormat`, `EventRef`, `CalendarEntry`; contrato `Draft`/`Fact`/`ChartRef`/`Segment`/`Source` (`vessel schema` exporta o JSON Schema).
- `cache/`: `FileCache` (escrita atômica, devolve a última versão salva se a fonte falhar) e políticas `Forever`, `Ttl` e `ParcFerme` (sessão encerrada e assentada nunca expira; `TIMING_SETTLE` 2 h, `RESULTS_SETTLE` 24 h).
- `sources/`: calendário do FastF1 + iCal oficial da F1; `schedule.reconcile` deixa o iCal vencer nos horários.
- `charts/`: `Chart(title, subtitle, preset, theme)` com tema escuro padrão, presets X 1600×900, feed 1080×1350 e story 1080×1920, e `save()` que escreve o rodapé "Dados: <fontes> · @1caiocarvalho" e devolve `ChartRef`.
- CLI (typer): `vessel version | doctor | schema | agenda`.

## Regras de gráfico

- Gráficos usam `vessel.charts.Chart`; nunca `pyplot` (sem estado global).
- Título diz a conclusão ("Verstappen ganhou 9 posições"), subtítulo diz o que está plotado.
- Identidade nunca só por cor: com mais de uma série, rótulo direto (código do piloto) ao lado da linha ou barra.
- Um eixo y só. Grade recessiva, sem bordas desnecessárias.
- Cores de equipe e de composto vêm do FastF1 (`fastf1.plotting`), que é convenção do esporte.

## Fontes de dados

- FastF1 (sessões desde 2018) e Jolpica via `fastf1.ergast` (histórico). Cache do FastF1 em `settings.fastf1_cache_dir`.
- api-sports não é usada. Mudanças de calendário (ex.: GP do Bahrain 2026 realizado em Kuala Lumpur) são reais; confira notícias antes de tratar como erro de dados.
