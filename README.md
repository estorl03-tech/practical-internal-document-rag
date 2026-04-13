# Practical RAG Prototype

Enterprise-oriented RAG prototype for internal knowledge search.

> This repository is a local portfolio prototype, not a production-ready service.
> Do not commit real API keys, internal company documents, or sensitive business data.

## Portfolio Summary

This project is a backend-focused RAG prototype built to address the gap between a simple demo and something closer to real internal knowledge operations.

Problems this prototype focuses on:

- Search is not enough if answers cannot show evidence
- Old and new versions of the same document should not be mixed
- Inactive documents should stay managed without staying searchable
- Restricted documents should not leak into retrieval or answers
- Answering should fail safely when evidence is weak

What is implemented:

- Hybrid retrieval with query rewrite and reranking
- Evidence-first answering with `green / yellow / red` safety signals
- Document lifecycle management: create, inspect, update, deactivate
- Metadata-aware retrieval using `version`, `updated_at`, and `document_group`
- Minimal ACL using `access_level` and `user_role`
- Regression coverage for retrieval, answer behavior, document updates, and access control

What this project is meant to demonstrate:

- Understanding of practical RAG failure modes
- Ability to separate retrieval, answer generation, document management, and evaluation concerns
- Ability to move from manual QA to automated regression checks
- Ability to add operational concepts like versioning and access control without overcomplicating the first implementation

In other words, this repository is best understood as a prototype that has started to solve the core operational problems of internal-document RAG, rather than a finished production system.

It directly addresses common real-world problems such as:

- unsupported answers that still sound confident
- mixing old and new versions of the same policy
- accidentally retrieving inactive documents
- leaking restricted documents into retrieval or answers
- relying on manual QA that cannot be replayed

What it does **not** fully solve yet:

- real authentication and identity-linked authorization
- richer ACL models for teams, projects, and individual users
- audit logging and operational accountability
- robust ingestion quality across messy PDFs and other file formats
- retrieval quality validation on larger document collections

## Current Status

- **Backend**
  Retrieval, answer generation, document management, active/inactive control, latest-version preference, minimal ACL, PDF upload, and delete API are implemented.
- **UI**
  The `/demo` page shows search, answer review, ACL differences, PDF upload, and `green / yellow / red` safety behavior in a single screen.
- **Quality**
  Retrieval, answer behavior, access control, document updates, PDF upload, and delete behavior are covered by regression tests.
- **Docs**
  README, architecture notes, and QA notes explain what is implemented now, what is intentionally minimal, and what would be company-specific in a real deployment.

## Demo UI

Open `http://127.0.0.1:8000/demo` to try the portfolio UI.

The demo is designed to make three behaviors easy to see:

1. `一般社員 -> red`
   A restricted or weakly-grounded question should stop safely instead of producing a confident-looking answer.
2. `人事 -> green`
   The same question can be answered once the viewer has access to the relevant HR document.
3. `PDF upload -> yellow`
   A newly uploaded PDF can be used immediately, while still responding cautiously when evidence is usable but not yet strong enough for a full `green`.

Recommended screenshot set for the portfolio:

- `一般社員` asking `人事評価資料はどこで確認できますか？`
  This shows safe refusal, no leaked evidence, and the fallback behavior for `red`.
- `人事` asking the same question
  This shows ACL-based retrieval, answer generation, and `used_source_summaries` with the relevant HR document.
- A PDF upload followed by `テレワークの申請はどこから行いますか？`
  This shows ingestion, retrieval from uploaded content, and a cautious `yellow` answer based on extracted evidence.

### Screenshot: `一般社員 -> red`

一般社員では権限外の質問に十分な根拠を集められず、回答を停止する例です。

![一般社員での安全停止](docs/images/demo-red.png)

### Screenshot: `人事 -> green`

人事ロールでは人事向け文書にアクセスできるため、同じ質問でも根拠付きで回答できる例です。

![人事ロールでの根拠付き回答](docs/images/demo-green.png)

### Screenshot: `PDF upload -> yellow`

PDF をアップロードして検索対象に追加し、根拠強度に応じて慎重に回答する例です。

![PDFアップロード後の慎重回答](docs/images/demo-yellow.png)

## What This Project Covers

- Document ingestion
- Paragraph-first chunking
- Embedding generation with OpenAI
- Vector search with Postgres + pgvector
- Answer generation with retrieved context
- Source-aware responses
- Document metadata management
- Active/inactive document control

## Architecture Overview

Core backend flow:

1. Documents are stored with metadata such as `version`, `is_active`, `document_group`, and `access_level`
2. Document content is chunked and embedded for retrieval
3. `/search` applies active filtering, ACL filtering, latest-version preference, hybrid scoring, and reranking
4. `/ask` reuses the same retrieval pipeline and only answers from retrieved evidence
5. Answer behavior is controlled through `green / yellow / red` thresholds rather than a single binary rule

Important design choices:

- `document_group` keeps multiple versions of the same document series related
- `updated_at` is the primary latest-version signal, with `version` as a tie-breaker
- `access_level` is intentionally minimal to show the ACL concept without hard-coding company-specific auth
- `used_sources` and `used_source_summaries` separate raw retrieval candidates from the evidence actually used in the answer

## Quick Start

### 1. Start the database

```powershell
docker compose up -d
```

### 2. Set your API key in the current terminal

```powershell
$env:OPENAI_API_KEY="sk-..."
```

The API key should be set only in your local shell or local environment file and must not be committed to Git.

### 3. Start the API server

```powershell
uv run uvicorn app.main:app --reload
```

### 4. Open the API docs

- `http://127.0.0.1:8000/docs`

## Main Endpoints

### System
- `GET /health`
- `GET /db-health`

### Document Management

Use these endpoints to register, inspect, update, and deactivate documents while keeping chunked retrieval data in sync.

- `POST /documents`
- `GET /documents`
- `GET /documents/{document_id}`
- `PATCH /documents/{document_id}`
- `PATCH /documents/{document_id}/active`
- `GET /documents/{document_id}/chunks`

### Retrieval

- `POST /search`

### Answering

- `POST /ask`

## Document Metadata Policy

Each document now carries the following metadata.

- `version`: simple document version label such as `v1`
- `is_active`: whether the document should be used for current retrieval and answering
- `document_group`: groups multiple versions of the same document series
- `access_level`: simple access control label such as `public` or `hr`
- `created_at`: when the document was first registered
- `updated_at`: when the document metadata was last updated

### Document update behavior

- `PATCH /documents/{document_id}` can update `title`, `source`, `content`, `version`, `is_active`, `document_group`, and `access_level`
- If `title`, `source`, or `content` changes, the document chunks are rebuilt
- Rebuilt chunks are re-embedded using the latest `title + chunk content` retrieval text
- This makes `updated_at` meaningful for actual content evolution, not just active-flag changes

#### Example: update an existing document

Request:

```json
{
  "title": "育児休業の申請ルール",
  "source": "childcare_policy_v2.pdf",
  "content": "育児休業は人事システムから申請します。\n育児休業の延長申請は人事ポータルから行います。\n延長申請には本人確認書類の添付が必要です。\n申請期限までに上長確認を完了してください。",
  "version": "v2",
  "is_active": true,
  "document_group": "childcare_policy",
  "access_level": "public"
}
```

Use with:

```powershell
PATCH /documents/1
```

### Active / inactive behavior

- Inactive documents remain visible in `GET /documents`
- Inactive documents are excluded from `POST /search`
- Inactive documents are also excluded from `POST /ask` because answering uses the same retrieval pipeline

### Access control behavior

- Documents are registered with an `access_level`
- `public` documents are visible to every `user_role`
- Non-public documents are visible only when `user_role` matches `access_level`
- `POST /search` and `POST /ask` accept `user_role` and apply the same access filter before retrieval

#### Example: search as a specific role

```json
{
  "query": "人事評価資料はどこで確認できますか？",
  "top_k": 3,
  "user_role": "hr"
}
```

### Answer safety signals

The answer pipeline now returns:

- `used_sources`: the subset of retrieved sources actually used to build the answer
- `answer_level`: `green`, `yellow`, or `red`

Interpretation:

- `green`: evidence is strong enough for a normal answer
- `yellow`: answer is returned, but with a more cautious tone
- `red`: evidence is too weak, so the system refuses to answer

The `confidence` field is still returned, but it should be treated as a reference score based on the average score of `used_sources`, not as the sole answer/no-answer decision.

## Development Notes

- Docker is used for the local Postgres + pgvector database.
- The OpenAI API key should be provided through environment variables.
- This project currently uses `Base.metadata.create_all()` for local development.
- For production-style evolution, migrations, logging, stricter access control, and fuller evaluation coverage should be added.

## GitHub Publishing Notes

- This repository is intended for local development and portfolio demonstration.
- Do not publish real internal documents, personal information, or company-confidential PDFs.
- Only include self-authored sample files, clearly fictional documents, or materials you have the right to redistribute.
- Before publishing, confirm that no API keys, `.env` files, local databases, or transient logs are included in the repository.

## What I Would Build Next

Some next steps are highly company-specific, so this prototype intentionally stops short of fully implementing them:

- Authentication-linked access control instead of request-body `user_role`
- Richer ACL models for department, project, and user-level permissions
- Audit logging for who searched what and which sources were used

Other next steps are common RAG quality problems regardless of company context:

- Better ingestion quality for PDF and document formats beyond plain text
- Stronger retrieval evaluation on medium-sized and larger document sets
- A lightweight UI for search, answer review, source inspection, and safe fallback when answers are `red`

## Detailed Guide

See [docs/development-guide.md](/C:/Users/estor/RAG/docs/development-guide.md) for:

- startup best practices
- testing strategy
- safe edit boundaries
- coding conventions
- deployment cautions
- important files

See [docs/architecture-overview.md](/C:/Users/estor/RAG/docs/architecture-overview.md) for:

- backend responsibility boundaries
- retrieval and answer flow
- versioning and ACL design choices
- what is intentionally minimal in this prototype
