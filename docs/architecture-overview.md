# Architecture Overview

## Goal

This project is a practical RAG backend for internal knowledge search.
It is designed to go beyond a simple semantic-search demo by addressing a few common enterprise concerns:

- evidence-first answering
- safe refusal when evidence is weak
- document lifecycle management
- latest-version preference
- minimal access control
- regression-oriented evaluation

## System Shape

The system is intentionally split into a few small responsibilities.

### API layer

- [app/main.py](/C:/Users/estor/RAG/app/main.py)

Responsibilities:

- receive requests
- open and close database sessions
- call service-layer functions
- keep endpoints thin

### Retrieval layer

- [app/services/search_service.py](/C:/Users/estor/RAG/app/services/search_service.py)

Responsibilities:

- rewrite queries
- embed the rewritten query
- retrieve candidate chunks from pgvector
- apply lexical + vector hybrid scoring
- apply minimal ACL filtering
- prefer the latest document within the same `document_group`
- rerank the filtered results

### Answer layer

- [app/services/ask_service.py](/C:/Users/estor/RAG/app/services/ask_service.py)
- [app/embeddings.py](/C:/Users/estor/RAG/app/embeddings.py)

Responsibilities:

- choose whether the system should answer
- expose `green / yellow / red` safety signals
- build answer context from retrieved evidence
- generate evidence-first answers
- return both raw candidates and actually used sources

### Persistence layer

- [app/models.py](/C:/Users/estor/RAG/app/models.py)
- [app/database.py](/C:/Users/estor/RAG/app/database.py)

Responsibilities:

- store document metadata
- store chunked retrieval data
- keep document and chunk relationships explicit

### Evaluation layer

- [docs/qa-cases.md](/C:/Users/estor/RAG/docs/qa-cases.md)
- [docs/eval-cases.yaml](/C:/Users/estor/RAG/docs/eval-cases.yaml)
- [tests/test_search_service.py](/C:/Users/estor/RAG/tests/test_search_service.py)
- [tests/test_ask_service.py](/C:/Users/estor/RAG/tests/test_ask_service.py)
- [tests/test_document_active_flow.py](/C:/Users/estor/RAG/tests/test_document_active_flow.py)
- [tests/test_document_update_flow.py](/C:/Users/estor/RAG/tests/test_document_update_flow.py)

Responsibilities:

- keep representative QA cases visible
- move stable expectations into automated regression tests
- verify retrieval, answering, document management, and access control behavior

## Retrieval Flow

1. A user sends `/search` or `/ask`.
2. The query is rewritten for retrieval.
3. The rewritten query is embedded.
4. Candidate chunks are fetched from active documents only.
5. Access control is applied before scoring.
6. Hybrid scores are computed from vector similarity and lexical overlap.
7. Results are filtered so older versions in the same `document_group` are dropped.
8. Remaining results are reranked.
9. `/search` returns ranked evidence candidates.
10. `/ask` reuses the same retrieval output and decides whether to answer.

## Why These Design Choices Exist

### `green / yellow / red`

A single binary answer/no-answer threshold is often too blunt.
This prototype uses three levels instead:

- `green`: normal answer
- `yellow`: cautious answer with weaker evidence
- `red`: refusal

This makes the system easier to operate safely in realistic internal-search scenarios.

### `used_sources` and `used_source_summaries`

`sources` shows the retrieved candidate set.
`used_sources` shows what the answer actually relied on.
`used_source_summaries` compresses those sources into document-level labels that are easier to display in UI.

This keeps answer transparency usable without forcing the frontend to reconstruct source meaning from raw chunk lists.

### `document_group`

Real document collections often contain multiple versions of the same policy.
`document_group` lets the system treat those versions as one series.

This enables:

- latest-version preference
- safer update handling
- clearer operational semantics than trying to infer version families from filenames alone

### `updated_at` first, `version` second

Latest-version preference uses:

1. `updated_at` as the primary signal
2. `version` as a tie-breaker

This is more reliable than trusting version labels alone while still handling equal timestamps predictably.

### `access_level` and `user_role`

This repo intentionally uses a very small ACL model:

- documents have `access_level`
- requests provide `user_role`
- `public` is visible to everyone
- non-public documents require role match

This is not a full enterprise auth model, but it demonstrates the most important product behavior:
restricted documents should not appear in retrieval or leak into answers.

## Document Lifecycle Flow

1. A document is registered with metadata.
2. Content is chunked and embedded.
3. A document can be updated without changing its identity.
4. If search-relevant fields change, chunks are rebuilt and re-embedded.
5. A document can be marked inactive instead of deleted.
6. Inactive documents remain inspectable but are excluded from retrieval and answering.

This supports a more realistic internal-document workflow than treating ingestion as write-once data.

## What This Prototype Proves

This project shows that the backend can evolve from a basic RAG demo into something that begins to resemble real internal knowledge operations:

- retrieval quality is improved, not left as raw semantic search
- answer behavior is controlled, not always-on
- document updates propagate to retrieval and answers
- latest-version handling is explicit
- minimal ACL prevents obvious leakage
- manual QA has been partially converted into automated regression coverage

## What Is Still Intentionally Minimal

The following are intentionally not fully built out yet:

- real authentication / SSO integration
- rich ACL inheritance across departments, projects, and individuals
- audit logging
- frontend UX
- large-scale evaluation on hundreds of documents
- migration-based schema evolution

Those are important for production, but this repository is intentionally scoped as a practical portfolio-grade backend prototype.
