---
name: api-conventions
description: Conventions for a vessel HTTP API serving drafts and charts to the frontend — resources, status codes, response shape aligned with the draft.json contract. Auto-loaded when editing API code.
user-invocable: false
paths:
  - "src/vessel/api/**"
---

The API is a thin read layer over what the pipeline already wrote; it never computes a number.

## Resources

- Plural, kebab-case paths, versioned: `/v1/drafts`, `/v1/drafts/{season}/{slug}/{segment}`, `/v1/events/{season}`, `/v1/event-status/{season}`.
- Charts are served as files from the draft directory (`ChartRef.path` resolved under it; reject `..` and absolute paths).
- Read-only by default. Any write (e.g. editing `config/event_status.toml`) needs an explicit decision and validation through the same pydantic models.

## Responses

- JSON bodies are the pydantic models dumped as-is: **snake_case** fields and lowercase enum values, exactly like `draft.json` (`vessel schema`). Don't re-case for the frontend; generate TS types from the JSON Schema instead.
- Datetimes ISO 8601 in UTC; the frontend converts to `America/Cuiaba`.
- Status codes: 200, 404 (unknown season/round/segment), 422 (invalid params), 503 when a source is unavailable and no cached version exists. Never 200 for errors.
- Error shape: `{"error": {"code": "UPPER_SNAKE_CASE", "message": "..."}}`; no stack traces, paths or tokens.

## Layering

- Routes do HTTP only; reading drafts/config lives in plain functions reused by the CLI.
- Never import FastF1/Ergast in route modules; the API reads curated/out files, it doesn't fetch.
